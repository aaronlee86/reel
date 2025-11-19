#!/usr/bin/env python3
"""
TOEIC Question Verification Script
Validates TOEIC Listening questions (Parts 1-4) using OpenAI GPT-4o
"""

import sqlite3
import argparse
import os
import sys
import base64
import json
import logging
from typing import Optional, Dict, List, Tuple
from openai import OpenAI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

ChatGPT_MODEL_VER = "gpt-5-mini-2025-08-07"

class ToeicVerifier:
    """Main class for verifying TOEIC questions using OpenAI"""

    def __init__(self, db_path: str, api_key: Optional[str] = None):
        """
        Initialize the verifier

        Args:
            db_path: Path to SQLite database
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
        """
        self.db_path = db_path
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')

        if not self.api_key:
            logger.error("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")

        self.client = OpenAI(api_key=self.api_key)
        self.stats = {
            'processed': 0,
            'valid': 0,
            'invalid': 0,
            'errors': 0
        }

    def connect_db(self) -> sqlite3.Connection:
        """Connect to the SQLite database"""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found: {self.db_path}")
        return sqlite3.connect(self.db_path)

    def get_questions(self, part: Optional[int] = None,
                     level: Optional[int] = None,
                     count: Optional[int] = None,
                     start_id: Optional[int] = None) -> List[Dict]:
        """
        Query questions from database with filters

        Args:
            part: Filter by TOEIC part (1-4)
            level: Filter by difficulty level
            count: Limit number of questions

        Returns:
            List of question dictionaries
        """
        conn = self.connect_db()
        cursor = conn.cursor()

        # Build query with filters
        query = "SELECT * FROM questions WHERE valid = 0"
        params = []

        if start_id is not None: # New logic for --id
            query += " AND id >= ?"
            params.append(start_id)

        if part is not None:
            query += " AND part = ?"
            params.append(part)

            # Part 1 requires images
            if part == 1:
                query += " AND img IS NOT NULL"

        if level is not None:
            query += " AND level = ?"
            params.append(level)

        query += " ORDER BY id ASC"

        if count is not None:
            query += " LIMIT ?"
            params.append(count)

        cursor.execute(query, params)
        columns = [description[0] for description in cursor.description]
        questions = [dict(zip(columns, row)) for row in cursor.fetchall()]

        conn.close()
        return questions

    def encode_image(self, image_path: str) -> Optional[str]:
        """
        Encode image to base64

        Args:
            image_path: Path to image file

        Returns:
            Base64 encoded image string or None if error
        """
        try:
            if not os.path.exists(image_path):
                logger.warning(f"Image not found: {image_path}")
                return None

            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.warning(f"Error encoding image: {e}")
            return None

    def get_image_mime_type(self, image_path: str) -> str:
        """Determine MIME type from file extension"""
        ext = os.path.splitext(image_path)[1].lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        return mime_types.get(ext, 'image/jpeg')

    def verify_question(self, question: Dict) -> int:
        """
        Verify a single question with OpenAI

        Args:
            question: Question dictionary from database

        Returns:
            validation status: 1 (valid), -1 (invalid), -2 (error),
            status message
        """
        try:
            # Build the prompt based on part
            prompt = self._build_prompt(question)
            logger.info(f"Prompt:\n{prompt}")

            # Prepare messages
            messages = []

            # Handle Part 1 - Image questions
            if question['part'] in (1,3,4) and question['img']:
                base64_image = self.encode_image(os.path.join('..', 'assets','photo','toeic',f'p{question['part']}',question['img']))
                if base64_image is None:
                    return -2, "Image encoding error"

                mime_type = self.get_image_mime_type(question['img'])
                messages.append({
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_image", "image_url": f"data:{mime_type};base64,{base64_image}"}
                    ]
                })
            else:
                messages.append({
                    "role": "user",
                    "content": [{"type": "input_text", "text": prompt}]
                })

            # Call OpenAI API
            response = self.client.responses.create(
                model=ChatGPT_MODEL_VER,
                input=messages
            )

            logger.info(f"  OpenAI Response: {response}")
            logger.info(f"  type of OpenAI Response: {type(response)}")
            answer_obj = json.loads(response.output_text.strip())
            #answer_obj = json.loads('[{"A": 80, "B": 10, "C": 5, "D": 5}, {"A": 5, "B": 85, "C": 5, "D": 5}, {"A": 100, "B": 0, "C": 0, "D": 0}]')
            #answer_obj = json.loads('{"A": 80, "B": 10, "C": 5, "D": 5}')
            logger.info(f"  Extracted Answer Text: {answer_obj}")
            # Extract answer from response
            result = self._extract_answer(answer_obj, question['part'])
            if result is None:
                errstr = f"Could not parse response: {response}"
                logger.warning(errstr)
                return -2, errstr

            openai_answer, confidence = result

            # check confidence and answer
            for c in confidence:
                if c < 85:
                    errstr = f"Low confidence score: {openai_answer} {confidence}"
                    logger.warning(errstr)
                    return -1, errstr

            # Compare with database answer
            print(f"openai_answer and type: {openai_answer}, {type(openai_answer)}")
            db_answer = question['answer'].strip().upper()
            if len(db_answer) > 1:
                db_answer = json.loads(question['answer'].strip().upper())
            else:
                db_answer = [db_answer]
            print(f"db_answer and type: {db_answer}, {type(db_answer)}")
            # Check if answers match
            if openai_answer != db_answer:
                # Answers don't match - mark as invalid regardless of confidence
                return -1, f"Answer mismatch: OpenAI: {openai_answer} with confidence {confidence}"
            else:
                return 1, f"Valid answer with confidence: {confidence}"
        except Exception as e:
            logger.error(f"Exception: {e}")
            return -2, f"Exception: {e}"

    def _build_prompt(self, question: Dict) -> str:
        """Build the prompt for OpenAI based on TOEIC part"""
        part = question['part']
        print("question:", question)

        if part == 3:
            speaker_info = []

            for sex,accent in zip(json.loads(question['sex']),json.loads(question['accent'])):
                speaker_info.append(f"{sex} with {accent} accent")

            conversation_exchanges = ""
            for speaker, exchange in zip(speaker_info, json.loads(question['prompt'])):
                conversation_exchanges += f'"{speaker}": "{exchange}"\n'

        if part in [3, 4]:
            # For parts 3 and 4, parse JSON fields
            question['question'] = json.loads(question.pop('question'))
            question['A'] = json.loads(question.pop('A'))
            question['B'] = json.loads(question.pop('B'))
            question['C'] = json.loads(question.pop('C'))
            question['D'] = json.loads(question.pop('D'))

        if part == 1:
            # Part 1: Photographs - 4 statements describing an image
            prompt = f"""You are solving a TOEIC Listening Part 1 question (Photographs).

Look at the image and determine which statement best describes what you see.

Options:
A) {question['A']}
B) {question['B']}
C) {question['C']}
D) {question['D']}

Give correctiness for each option, which is rated from 0 to 100. The sum of correctness for all options should be no larger than 100.
if two or more options are equally correct, distribute the scores evenly among them.
Respond ONLY in this exact json format:
{{"A":[Confidence Score 0-100],"B":[Confidence Score 0-100],"C":[Confidence Score 0-100],"D":[Confidence Score 0-100]}}

Example: {{"A":0,"B":5,"C":91,"D":4}}
Example: {{"A":0,"B":50,"C":50,"D":0}}
Example: {{"A":0,"B":0,"C":0,"D":0}}

Do not include any other text."""

        elif part == 2:
            # Part 2: Question-Response - 3 responses to a question
            prompt = f"""You are solving a TOEIC Listening Part 2 question.

Question: {question['question']}

Responses:
A) {question['A']}
B) {question['B']}
C) {question['C']}

Give correctiness for each response, which is rated from 0 to 100. The sum of correctness for all responses should be no larger than 100.
if two or more options are equally correct, distribute the scores evenly among them.
Respond ONLY in this exact json format:
{{"A":[Confidence Score 0-100],"B":[Confidence Score 0-100],"C":[Confidence Score 0-100]}}

Example: {{"A":20,"B":5,"C":75}}
Example: {{"A":33,"B":33,"C":33}}
Example: {{"A":0,"B":0,"C":0}}

Do not include any other text."""

        elif part == 3:
            # Part 3: Conversations - conversation text + question + 4 options
            prompt = f"""You are solving a TOEIC Listening Part 3 question (Conversations).

Conversation:
{conversation_exchanges}
Question1: {question['question'][0]}
Options:
A) {question['A'][0]}
B) {question['B'][0]}
C) {question['C'][0]}
D) {question['D'][0]}

Question2: {question['question'][1]}
Options:
A) {question['A'][1]}
B) {question['B'][1]}
C) {question['C'][1]}
D) {question['D'][1]}

Question3: {question['question'][2]}
Options:
A) {question['A'][2]}
B) {question['B'][2]}
C) {question['C'][2]}
D) {question['D'][2]}

Give correctiness for each option, which is rated from 0 to 100. The sum of correctness for all option should be no larger than 100.
Especially, pay attention to the sex of the speaker in the question and option. If the option describes an behavior/intention or action but the actor is different in the conversation, should give 0 score to the option.
if two or more options are equally correct, distribute the scores evenly among them.
Respond ONLY in this exact json array format for questions 1, 2, and 3:
[{{"A":[Confidence Score 0-100],"B":[Confidence Score 0-100],"C":[Confidence Score 0-100],"D":[Confidence Score 0-100]}},
{{"A":[Confidence Score 0-100],"B":[Confidence Score 0-100],"C":[Confidence Score 0-100],"D":[Confidence Score 0-100]}},
{{"A":[Confidence Score 0-100],"B":[Confidence Score 0-100],"C":[Confidence Score 0-100],"D":[Confidence Score 0-100]}}]

Example: [{{"A":10,"B":20,"C":60,"D":10}},{{"A":5,"B":15,"C":70,"D":10}},{{"A":25,"B":25,"C":25,"D":25}}]
Do not include any other text."""

        elif part == 4:
            # Part 4: Talks - talk/monologue text + question + 4 options
            prompt = f"""You are verifying a TOEIC Listening Part 4 question (Talks).

Talk:
{question['prompt']}

Question1: {question['question'][0]}
Options:
A) {question['A'][0]}
B) {question['B'][0]}
C) {question['C'][0]}
D) {question['D'][0]}

Question2: {question['question'][1]}
Options:
A) {question['A'][1]}
B) {question['B'][1]}
C) {question['C'][1]}
D) {question['D'][1]}

Question3: {question['question'][2]}
Options:
A) {question['A'][2]}
B) {question['B'][2]}
C) {question['C'][2]}
D) {question['D'][2]}

Give correctiness for each option, which is rated from 0 to 100. The sum of correctness for all option should be no larger than 100.
if two or more options are equally correct, distribute the scores evenly among them.
Respond ONLY in this exact json array format for questions 1, 2, and 3:
[{{"A":[Confidence Score 0-100],"B":[Confidence Score 0-100],"C":[Confidence Score 0-100],"D":[Confidence Score 0-100]}},
{{"A":[Confidence Score 0-100],"B":[Confidence Score 0-100],"C":[Confidence Score 0-100],"D":[Confidence Score 0-100]}},
{{"A":[Confidence Score 0-100],"B":[Confidence Score 0-100],"C":[Confidence Score 0-100],"D":[Confidence Score 0-100]}}]

Example: [{{"A":10,"B":20,"C":60,"D":10}},{{"A":5,"B":15,"C":70,"D":10}},{{"A":25,"B":25,"C":25,"D":25}}]
Do not include any other text."""

        else:
            # Fallback for unknown parts
            prompt = None

        return prompt

    def _extract_answer(self, response_json: str, part: int):
        """
        Extract answer letter and confidence score from OpenAI response

        Args:
            response_json: Full response from OpenAI (format: a json {'A':xx,'B':yy,'C':zz,...} )
            part: TOEIC part number (optional, for validation)

        Returns:
            Tuple of (answer letter, confidence score) or None if parsing fails
        """
        # Find the key-value pair with the max value
        # Note: If there's a tie, this returns the *first* one found

        # Validate response_json is in expected format
        if isinstance(response_json, dict):
            response_json = [response_json]

        if not isinstance(response_json, list):
            logger.warning(f"Unexpected response format: {type(response_json)}")
            return None

        valid_answers = {'A', 'B', 'C', 'D'} if part != 2 else {'A', 'B', 'C'}

        answers = []
        scores = []

        for answer_dict in response_json:
            answer_dict = {k: v for k, v in answer_dict.items() if k in valid_answers}
            # make sure there are exactly 4 keys
            if len(answer_dict) != len(valid_answers):
                logger.warning(f"Expected 3/4 options for Part {part}, got: {answer_dict.keys()}")
                return None
            # make sure the sum of values is 100
            if sum(answer_dict.values()) > 100:
                logger.warning(f"Expected sum of confidence scores to be 100, got: {sum(answer_dict.values())}")
                return None

            answer, score = max(answer_dict.items(), key=lambda item: item[1])
            answers.append(answer)
            scores.append(score)

        return answers, scores

    def update_question_validity(self, question_id: int, valid: int, status: str):
        """
        Update the valid field in database

        Args:
            question_id: Question ID
            valid: Validation status (1, -1, or 0)
        """
        conn = self.connect_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE questions SET valid = ?, valid_status = ? WHERE id = ?", (valid, status, question_id))
        conn.commit()
        conn.close()

    def process_questions(self, part: Optional[int] = None,
                         level: Optional[int] = None,
                         count: Optional[int] = None,
                         start_id: Optional[int] = None):
        """
        Main processing loop

        Args:
            part: Filter by TOEIC part
            level: Filter by difficulty level
            count: Limit number of questions
        """
        questions = self.get_questions(part, level, count, start_id)

        if not questions:
            logger.info("No questions found matching the criteria.")
            return

        total = len(questions)
        logger.info(f"Found {total} question(s) to verify")
        logger.info("=" * 70)

        for idx, question in enumerate(questions, 1):
            logger.info(f"[{idx}/{total}] Processing Question ID: {question['id']}")
            logger.info(f"  Part: {question['part']} | Level: {question['level']}")

            # Log different fields based on part
            if question['part'] == 1:
                # Part 1: Image + statements
                logger.info(f"  Type: Photographs (Image + 4 statements)")
                if question['img']:
                    logger.info(f"  Image: {question['img']}")
                else:
                    logger.warning(f"  WARNING: Part 1 question missing image")
            elif question['part'] == 2:
                # Part 2: Question + 3 responses
                logger.info(f"  Type: Question-Response")
                logger.info(f"  Question: {question['question'][:80]}...")
            elif question['part'] == 3:
                # Part 3: Conversation + question + 4 options
                logger.info(f"  Type: Conversations")
                if question['prompt']:
                    logger.info(f"  Conversation: {question['prompt'][:80]}...")
                logger.info(f"  Question: {question['question'][:80]}...")
            elif question['part'] == 4:
                # Part 4: Talk + question + 4 options
                logger.info(f"  Type: Talks")
                if question['prompt']:
                    logger.info(f"  Talk: {question['prompt'][:80]}...")
                logger.info(f"  Question: {question['question'][:80]}...")

            logger.info(f"  DB Answer: {question['answer']}")

            # Verify question
            validation, result = self.verify_question(question)

            if validation == -2:
                self.stats['errors'] += 1
            elif validation == -1:
                self.stats['invalid'] += 1
            else:
                self.stats['valid'] += 1

            # Update database
            self.update_question_validity(question['id'], validation, result)

            self.stats['processed'] += 1

        self._print_summary()

    def _print_summary(self):
        """Print final summary statistics"""
        logger.info("=" * 70)
        logger.info("VERIFICATION SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Total Processed: {self.stats['processed']}")
        logger.info(f"Valid (matched):   {self.stats['valid']}")
        logger.info(f"Invalid (mismatch): {self.stats['invalid']}")
        logger.info(f"Errors (skipped):   {self.stats['errors']}")
        logger.info("=" * 70)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Verify TOEIC questions using OpenAI GPT-4o',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python verifyToeicQ.py --db=questions.db
  python verifyToeicQ.py --db=questions.db --part=1 --count=10
  python verifyToeicQ.py --db=questions.db --part=2 --level=3
        """
    )

    parser.add_argument('--db', required=True, help='Path to SQLite database')
    parser.add_argument('--part', type=int, choices=[1, 2, 3, 4],
                       help='Filter by TOEIC part (1-4)')
    parser.add_argument('--level', type=int, help='Filter by difficulty level')
    parser.add_argument('--count', type=int, help='Limit number of questions to process')
    parser.add_argument('--id', type=int, dest='start_id', help='Start verification from this Question ID (inclusive)')

    args = parser.parse_args()

    try:
        verifier = ToeicVerifier(args.db)
        verifier.process_questions(
            part=args.part,
            level=args.level,
            count=args.count,
            start_id=args.start_id
        )
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
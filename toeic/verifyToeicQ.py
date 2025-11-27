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
from typing import Optional, Dict, List, Type, Callable, Tuple
from openai import OpenAI
import importlib.util
from pydantic import BaseModel
from common import VerifyStatus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

ChatGPT_MODEL_VER = "gpt-5-mini-2025-08-07"


def convert_to_schema(q_dict: Dict) -> Dict:
    # Build script section
    part = q_dict['part']

    if part == 1:
        output_json = {
            "A": q_dict['A'][0],
            "B": q_dict['B'][0],
            "C": q_dict['C'][0],
            "D": q_dict['D'][0]
        }
    else:
        questions = q_dict['question']

        # Build questions section
        q_list = []
        num_q = len(questions)

        for i in range(num_q):
            q_list.append({
                "question": questions[i],
                "A": q_dict['A'][i],
                "B": q_dict['B'][i],
                "C": q_dict['C'][i]
            })
            if part != 2:
                # only part 2 has 3 options
                q_list[-1]['D'] = q_dict['D'][i]

        output_json = {
            "questions": q_list
        }

        if part == 3:
            script = []
            speakers = q_dict['sex']
            lines = q_dict['prompt']

            for spk, line in zip(speakers, lines):
                script.append({
                    "speaker": spk,
                    "line": line
                })

            output_json['script'] = script
        elif part == 4:
            output_json['talk'] = q_dict['prompt']

    return  output_json

def convert_to_schema_cross(q_dict: Dict, img: bool) -> Dict:
    # Build script section
    part = q_dict['part']

    if not part in (3,4):
        return None


    questions = q_dict['question']

    # Build questions section
    output_json = {
        "question": questions[2],
        "A": q_dict['A'][2],
        "B": q_dict['B'][2],
        "C": q_dict['C'][2],
        "D": q_dict['D'][2]
    }

    if img:
        output_json['img_prompt'] = q_dict['img_prompt']
    elif part == 3:
        script = []
        speakers = q_dict['sex']
        lines = q_dict['prompt']

        for spk, line in zip(speakers, lines):
            script.append({
                "speaker": spk,
                "line": line
            })

        output_json['script'] = script
    elif part == 4:
        output_json['talk'] = q_dict['prompt'][0]

    return  output_json


def load_prompt(part: int, prompt_type: str, img) -> str:
    """
    Load prompt from external text file.

    Returns:
        str: Prompt text
    """
    try:
        prompt_path = os.path.join('parts', f'part{part}', f'verify_{prompt_type}_prompt_{"with_img" if img else "without_img"}.txt')
        with open(prompt_path, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        logging.error(f"Prompt file not found: {prompt_path}")
        raise
    except Exception as e:
        logging.error(f"Error reading prompt file: {e}")
        raise

def load_cross_prompt(part: int, prompt_type: str, img) -> str:
    """
    Load prompt from external text file.

    Returns:
        str: Prompt text
    """
    try:
        prompt_path = os.path.join('parts', f'part{part}', f'cross_verify_{prompt_type}_prompt_{"with_img" if img else "without_img"}.txt')
        with open(prompt_path, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        logging.error(f"Prompt file not found: {prompt_path}")
        raise
    except Exception as e:
        logging.error(f"Error reading prompt file: {e}")
        raise

def load_cross_part_model(part: int, img: bool) -> Type[BaseModel]:
    # Construct the path to the Result.py file
    base_path = os.path.join('parts', f'part{part}')
    model_path = os.path.join(base_path, f'Cross_Verify_Result.py')

    try:
        # Check if file exists
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")

        # Dynamically import the module
        spec = importlib.util.spec_from_file_location(f"part{part}_model", model_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Find and return the PartResult class
        part_result_class = getattr(module, 'Result', None)

        if part_result_class is None:
            raise AttributeError(f"No Result class found in {model_path}")

        return part_result_class

    except (ImportError, FileNotFoundError, AttributeError) as e:
        print(f"Error importing model for part {part}: {e}")
        return None

def load_part_model(part: int, img: bool) -> Type[BaseModel]:
    """
    Dynamically import Result model from specific part directory

    Returns:
        Optional[Type[BaseModel]]: Imported Pydantic model or None if import fails
    """
    # Construct the path to the Result.py file
    base_path = os.path.join('parts', f'part{part}')
    model_path = os.path.join(base_path, f'Verify_Result_{'with_img' if img else 'without_img'}.py')

    try:
        # Check if file exists
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")

        # Dynamically import the module
        spec = importlib.util.spec_from_file_location(f"part{part}_model", model_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Find and return the PartResult class
        part_result_class = getattr(module, 'Result', None)

        if part_result_class is None:
            raise AttributeError(f"No Result class found in {model_path}")

        return part_result_class

    except (ImportError, FileNotFoundError, AttributeError) as e:
        print(f"Error importing model for part {part}: {e}")
        return None


class VerificationChain:
    def __init__(self):
        self.stages: List[Callable[[Dict, bool], Tuple[VerifyStatus, Optional[str]]]] = []

    def add_stage(
        self,
        verification_func: Callable[[Dict, bool], Tuple[VerifyStatus, Optional[str]]]
    ) -> 'VerificationChain':
        """
        Add a verification stage

        Ensures every stage follows the signature:
        func(question: Dict, img: bool) -> Tuple[VerifyStatus, Optional[str]]
        """
        self.stages.append(verification_func)
        return self

    def verify(self, question: Dict, img: bool = False) -> Tuple[VerifyStatus, Optional[str]]:
        """
        Execute verification stages in sequence

        Consistent parameters: question and img
        """
        status: VerifyStatus
        message: Optional[str]

        for stage in self.stages:
            try:
                status, message = stage(question, img)

                # Strict validation logic
                if status != VerifyStatus.VALID:
                    logger.warning(f"Verification failed at stage {stage.__name__}: {message}")
                    return status, message
            except Exception as e:
                logger.error(f"Error in verification stage {stage.__name__}: {e}")
                return VerifyStatus.ERROR, f"Exception in verification function {stage.__name__}: {e}"

        # If all stages pass
        return status, message

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
        self.verification_chain = self._setup_verification_chain()

    def _setup_verification_chain(self) -> VerificationChain:
        """
        Set up verification chain with consistent parameters
        """
        return (VerificationChain()
            .add_stage(self.verify_cross_audio)
            .add_stage(self.verify_cross_img)
            .add_stage(self.verify_question_similarity)
            .add_stage(self.verify_full)
        )

    def connect_db(self) -> sqlite3.Connection:
        """Connect to the SQLite database"""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found: {self.db_path}")
        return sqlite3.connect(self.db_path)

    def get_questions(self, part: Optional[int] = None,
                     level: Optional[int] = None,
                     count: Optional[int] = None,
                     start_id: Optional[int] = None,
                     img: bool = False ) -> List[Dict]:
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

        if img:
            query += " AND img IS NOT NULL AND img_prompt IS NOT NULL"
        else:
            query += " AND (img_prompt IS NULL OR img_prompt = '')"

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

    def verify_question_similarity(self, question: Dict, img: bool = False):
        if question['part'] in (3,4):
            questions = question['question']

            # Load a pre-trained Sentence Transformer model
            logging.info("loading Sentence Transformer module...")
            from sentence_transformers import SentenceTransformer, util
            sent_model = SentenceTransformer('all-MiniLM-L6-v2')
            logging.info("done")

            # check if the 3 questions are similar
            embeddings = sent_model.encode(questions, convert_to_tensor=True)
            cosine_scores = util.cos_sim(embeddings, embeddings)

            print(f"q1 = {questions[0]}")
            print(f"q2 = {questions[1]}")
            print(f"q3 = {questions[2]}")
            print(f"cosine: {cosine_scores}")

            threshold = 0.7
            if abs(cosine_scores[0][1].item()) > threshold or abs(cosine_scores[0][2].item()) > threshold or abs(cosine_scores[1][2].item()) > threshold :
                return VerifyStatus.FAIL_SIMILAR_QUESTION, f"too similar with thrshold > {threshold}. consine matrix: {cosine_scores}"

        return VerifyStatus.VALID, None

    def verify_cross_audio(self, question: Dict, img: bool = False):
        status, msg  = self._cross_verify(question, img=False)
        if status != VerifyStatus.VALID:
            return VerifyStatus.FAIL_AUDIO_ANSWER_MATCH, f"Audio reveals answer: {msg}"
        return VerifyStatus.VALID, msg


    def verify_cross_img(self, question: Dict, img: bool = False):
        status, msg = self._cross_verify(question, img=True)
        if status != VerifyStatus.VALID:
            return VerifyStatus.FAIL_IMAGE_ANSWER_MATCH, f"Image reveals answer: {msg}"
        return VerifyStatus.VALID, msg

    def _cross_verify(self, question: Dict, img: bool = False)-> Tuple[VerifyStatus, Optional[str]]:
        if not question['part'] in (3,4):
            return VerifyStatus.VALID, None

        try:
            # Build the prompt based on part
            system_prompt = load_cross_prompt(question['part'], 'system', img)
            user_prompt = load_cross_prompt(question['part'], 'user', img)
            json_schema = load_cross_part_model(question['part'], img)
        except Exception as e:
            logger.error(f"Error loading prompts or models: {e}")
            return VerifyStatus.ERROR, f"Error loading prompts or models: {e}"

        # Format user prompt with actual values
        user_prompt = user_prompt.format(
            question=convert_to_schema_cross(question, img)
        )

        db_vector = []
        # convert db answer to a vector
        for i in question['answer']:
            db_vector.append([100.0 if i == 'A' else 0.0, 100.0 if i == 'B' else 0.0, 100.0 if i == 'C' else 0.0, 100.0 if i == 'D' else 0.0])

        db_vector = db_vector[2]  # only verify the 3rd question

        # print prompts for debugging
        logger.debug(f"System Prompt:\n{system_prompt}\n")
        logger.info(f"User Prompt:\n{user_prompt}\n")

        # Prepare messages
        user_message = [{"type": "input_text", "text": user_prompt}]

        try:
            response = self.client.responses.parse(
                model=ChatGPT_MODEL_VER,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                text_format=json_schema
            )
            logging.info(f"total tokens {response.usage.total_tokens}")
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return VerifyStatus.ERROR, f"OpenAI API error: {e}"

        parsed_response = response.output_parsed

        response_dict = parsed_response.model_dump()
        json_str = parsed_response.model_dump_json(indent=2)
        logging.info(f" AI dict result={json_str}")

        ai_answer = response_dict['answer']

        # convert answer dict to a 4 number vector e.g. {"A": xx,"B":yy,"C":zz,"D":ww} to [xx, yy, zz, ww]
        ai_vector = [ai_answer['A'], ai_answer['B'], ai_answer['C'], ai_answer.get('D', 0)]
        logger.info(f"ai_vector: {ai_vector}")
        logger.info(f"db_vector: {db_vector}")

        # check length match
        if len(db_vector) != len(ai_vector):
            print(f"  Length mismatch: db_vector has {len(db_vector)} options, v_ai has {len(ai_vector)} options")
            return VerifyStatus.ERROR, f"Answer option length mismatch"
        # compute sum of absolute difference
        diff = sum(abs(a - b) for a, b in zip(db_vector, ai_vector))
        logger.info(f"  Computed diff: {diff}")
        # threshold for acceptance is 10
        threshold = 70
        if diff < threshold:
            print(f"  Match detected (diff {diff} < {threshold})")
            return VerifyStatus.INVALID, f"{ai_answer}"

        return VerifyStatus.VALID, ""

    def verify_full(self, question: Dict, img: bool = False):
        """
        Verify a single question with OpenAI
        Args:
            question: Question dictionary
            img: Whether to include image prompt
        Returns:
            validation status
            status message
        """

        try:
            # Build the prompt based on part
            system_prompt = load_prompt(question['part'], 'system', img)
            user_prompt = load_prompt(question['part'], 'user', img)
            json_schema = load_part_model(question['part'], img)
        except Exception as e:
            logger.error(f"Error loading prompts or models: {e}")
            return VerifyStatus.ERROR, f"Error loading prompts or models: {e}"

        # Format user prompt with actual values
        user_prompt = user_prompt.format(
            question=convert_to_schema(question)
        )

        db_vector = []
        # convert db answer to a vector
        for i in question['answer']:
            db_vector.append([100.0 if i == 'A' else 0.0, 100.0 if i == 'B' else 0.0, 100.0 if i == 'C' else 0.0, 100.0 if i == 'D' else 0.0])

        # print prompts for debugging
        logger.debug(f"System Prompt:\n{system_prompt}\n")
        logger.info(f"User Prompt:\n{user_prompt}\n")

        # Prepare messages
        user_message = [{"type": "input_text", "text": user_prompt}]
        if img and question['img']:
            img_name = question['img']
            try:
                img_path = os.path.join('..', 'assets','photo','toeic',f'p{question['part']}', img_name)
                base64_image = self.encode_image(img_path)
                if base64_image is None:
                    return VerifyStatus.ERROR, f"Image encoding error {img_path}"

                mime_type = self.get_image_mime_type(img_name)
                user_message.append({"type": "input_image", "image_url": f"data:{mime_type};base64,{base64_image}"})
            except Exception as e:
                logger.error(f"Error preparing image for question ID {question['id']}: {e}")
                return VerifyStatus.ERROR, f"Error preparing image: {e}"

        try:
            response = self.client.responses.parse(
                model=ChatGPT_MODEL_VER,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                text_format=json_schema
            )
            logging.info(f"total tokens {response.usage.total_tokens}")
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return VerifyStatus.ERROR, f"OpenAI API error: {e}"

        parsed_response = response.output_parsed

        response_dict = parsed_response.model_dump()
        json_str = parsed_response.model_dump_json(indent=2)
        logging.info(f" AI dict result={json_str}")

        ai_answer = response_dict['answer']

        # convert answer dict to a 4 number vector e.g. {"A": xx,"B":yy,"C":zz,"D":ww} to [xx, yy, zz, ww]
        ai_vector = [[a['A'],a['B'],a['C'],a.get('D',0)] for a in ai_answer]
        logger.info(f"ai_vector: {ai_vector}")
        logger.info(f"db_vector: {db_vector}")

        # compare db_vector and v1
        # verify number of answers match
        if len(db_vector) != len(ai_vector):
            print(f"Number of answers mismatch: db_vector has {len(db_vector)} answers, v1 has {len(ai_vector)} answers")
            return VerifyStatus.ERROR, f"Number of answers mismatch"

        for v_db, v_ai in zip(db_vector, ai_vector):
            print(f"Comparing db: {v_db} with ai: {v_ai}")
            # check length match
            if len(v_db) != len(v_ai):
                print(f"  Length mismatch: db_vector has {len(v_db)} options, v_ai has {len(v_ai)} options")
                return VerifyStatus.ERROR, f"Answer option length mismatch"
            # compute sum of absolute difference
            diff = sum(abs(a - b) for a, b in zip(v_db, v_ai))
            logger.info(f"  Computed diff: {diff}")
            # threshold for acceptance is 10
            threshold = 30
            if diff > threshold:
                print(f"  Mismatch detected (diff {diff} > {threshold})")
                return VerifyStatus.INVALID, f"Answer mismatch: AI: {ai_answer}"

        return VerifyStatus.VALID, f"{ai_answer}"

    def update_question_validity(self, question_id: int, valid: int, status: str):
        """
        Update the valid field in database

        Args:
            question_id: Question ID
            valid: Validation status
        """
        conn = self.connect_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE questions SET valid = ?, valid_status = ? WHERE id = ?", (valid, status, question_id))
        conn.commit()
        conn.close()

    def process_questions(self, part: Optional[int] = None,
                         level: Optional[int] = None,
                         count: Optional[int] = None,
                         start_id: Optional[int] = None,
                         img: bool = False):
        """
        Main processing loop

        Args:
            part: Filter by TOEIC part
            level: Filter by difficulty level
            count: Limit number of questions
        """
        questions = self.get_questions(part, level, count, start_id, img)

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
                if question['img']:
                    logger.info(f"  Image: {question['img']}")
                else:
                    logger.warning(f"  WARNING: Part 1 question missing image")
            elif question['part'] == 2:
                # Part 2: Question + 3 responses
                logger.info(f"  Question: {question['question'][:80]}...")
            elif question['part'] == 3:
                # Part 3: Conversation + question + 4 options
                if question['prompt']:
                    logger.info(f"  Conversation: {question['prompt'][:80]}...")
                logger.info(f"  Question: {question['question'][:80]}...")
            elif question['part'] == 4:
                # Part 4: Talk + question + 4 options
                if question['prompt']:
                    logger.info(f"  Talk: {question['prompt'][:80]}...")
                logger.info(f"  Question: {question['question'][:80]}...")

            # convert every to possible json format
            for key, value in question.items():
                if key in ['sex','prompt','question','answer','A','B','C','D']:
                    if isinstance(value, str):
                        if value.startswith('[') or value.startswith('{'):
                            question[key] = json.loads(value)
                        else:
                            question[key] = [value]

            logger.debug(f"  DB Answer: {question['answer']}")
            logger.debug(f"  DB Answer's type: {type(question['answer'])}")

            # Verify question
            verification_status, message = self.verification_chain.verify(question, img)

            if verification_status == VerifyStatus.ERROR:
                self.stats['errors'] += 1
            elif verification_status == VerifyStatus.VALID:
                self.stats['valid'] += 1
            else:
                self.stats['invalid'] += 1

            # Update database
            self.update_question_validity(question['id'], verification_status, message)

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
    parser.add_argument("--img", action='store_true', help="With image prompt")
    parser.add_argument('--count', type=int, help='Limit number of questions to process')
    parser.add_argument('--id', type=int, dest='start_id', help='Start verification from this Question ID (inclusive)')

    args = parser.parse_args()

    try:
        verifier = ToeicVerifier(args.db)
        verifier.process_questions(
            part=args.part,
            level=args.level,
            count=args.count,
            start_id=args.start_id,
            img=args.img
        )
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
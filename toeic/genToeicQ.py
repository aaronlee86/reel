#!/usr/bin/env python3
"""
genToeicQ.py - TOEIC Question Generator
Generates TOEIC questions and writes them to a SQLite database.

Usage:
    python genToeicQ.py --part=1 --level=2 --count=10 --db=sql.db
"""

import os
import argparse
import sqlite3
import sys
import json
import logging
from typing import List, Dict, Type, Tuple, Optional
from pydantic import BaseModel
import importlib.util
from common import VerifyStatus, VerificationChain
from time_text_replacer import convert_times_in_text

# Configure logging
def setup_logging() -> None:
    """Setup logging to both file and console."""
    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    log_level = logging.INFO

    # Create logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Remove any existing handlers
    logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(log_format))
    logger.addHandler(console_handler)


# Initialize the OpenAI client with API key from environment variable
logging.info("loading OpenAI module...")
from openai import OpenAI
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY")
)
logging.info("done")

def convert_to_schema_cross(q_dict: Dict, img: bool) -> Dict:
    # Build script section
    part = q_dict['part']

    if not part in (3,4):
        return None

    questions = json.loads(q_dict['question'])
    a = json.loads(q_dict['A'])
    b = json.loads(q_dict['B'])
    c = json.loads(q_dict['C'])
    d = json.loads(q_dict['D'])

    # Build questions section
    output_json = {
        "question": questions[2],
        "A": a[2],
        "B": b[2],
        "C": c[2],
        "D": d[2]
    }

    if img:
        output_json['img_prompt'] = q_dict['img_prompt']
    elif part == 3:
        script = []
        speakers = json.loads(q_dict['sex'])
        lines = json.loads(q_dict['prompt'])

        for spk, line in zip(speakers, lines):
            script.append({
                "speaker": spk,
                "line": line
            })

        output_json['script'] = script
    elif part == 4:
        output_json['talk'] = q_dict['prompt']

    return  output_json

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

def verify_options(question_data: Dict, img: bool) -> int:
    logging.info("Verifying answer options...")
    part = question_data.get('part')

    if part == 1:
        correct_answer = question_data.get('answer')
        if correct_answer not in ['A', 'B', 'C', 'D']:
            return VerifyStatus.FAIL_ANSWER_CHAR, f"Answer character is invalid: {correct_answer}"
    elif part == 2:
        correct_answer = question_data.get('answer')
        if correct_answer not in ['A', 'B', 'C']:
            return VerifyStatus.FAIL_ANSWER_CHAR, f"Answer character is invalid: {correct_answer}"
    elif part in [3, 4]:
        try:
            answers = json.loads(question_data.get('answer', '[]'))
            # if answers is a list of length 3 and all answers are in options, return 1
            if not (isinstance(answers, list) and len(answers) == 3 and
                all(ans in ['A', 'B', 'C', 'D'] for ans in answers)):
                return VerifyStatus.FAIL_ANSWER_CHAR, "Answer characters are invalid"
        except json.JSONDecodeError:
            return VerifyStatus.FAIL_ANSWER_CHAR, f"Answer is not valid JSON {question_data.get('answer')}"

    return VerifyStatus.UNVERIFIED, None

def verify_speakers(question_data: Dict, img: bool) -> int:
    part = question_data.get('part')
    if part != 3:
        return VerifyStatus.UNVERIFIED, None

    # check at most 3 people
    logging.info("Verifying number of speakers...")
    try:
        characters = set(json.loads(question_data['sex']))
        no_spakers = len(characters)
        if not 2 <= no_spakers <= 3:
            return VerifyStatus.FAIL_MORE_THAN_3_PEOPLE, f"{no_spakers} speakers"

        # check special rule for 3 people: never use the man or the woman
        if 'man2' in characters and 'the man' in question_data['question']:
            return VerifyStatus.FAIL_SPEAKER_NAMING, f"'the man' shows up in 2 men conversation"
        if 'woman2' in characters and 'the woman' in question_data['question']:
            return VerifyStatus.FAIL_SPEAKER_NAMING, f"'the woman' shows up in 2 women conversation"

    except json.JSONDecodeError:
        return VerifyStatus.ERROR, f"Sex is not valid JSON {question_data['sex']}"

    return VerifyStatus.UNVERIFIED, None

def verify_question_similarity(question: Dict, img: bool = False):
    if question['part'] in (3,4):
        logging.info("Verifying question similarity...")
        questions = json.loads(question['question'])

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
        logging.info(f"cosine: {cosine_scores}")

        threshold = 0.7
        if abs(cosine_scores[0][1].item()) > threshold or abs(cosine_scores[0][2].item()) > threshold or abs(cosine_scores[1][2].item()) > threshold :
            return VerifyStatus.FAIL_SIMILAR_QUESTION, f"too similar with thrshold > {threshold}. consine matrix: {cosine_scores}"

    return VerifyStatus.UNVERIFIED, None

def replace_time_with_readable(question_data: Dict, img: bool = False):
    logging.info("Replacing time with readable format...")

    part = question_data['part']
    to_be_replaced_fields = []
    if part == 1:
        to_be_replaced_fields = ['A', 'B', 'C', 'D']
    elif part == 2:
        to_be_replaced_fields = ['question', 'A', 'B', 'C']
    elif part in (3,4):
        to_be_replaced_fields = ['prompt']

    for field in to_be_replaced_fields:
        question_data[field] = convert_times_in_text(question_data[field])

    return VerifyStatus.UNVERIFIED, "Prevalidated"

def stamping(question: Dict, img: bool = False):
    logging.info("Stamping question...")
    # just a placeholder for future use
    return VerifyStatus.UNVERIFIED, "Prevalidated"

def load_prompt(part: int, prompt_type: str, img) -> str:
    """
    Load prompt from external text file.

    Returns:
        str: Prompt text
    """
    try:
        prompt_path = os.path.join('parts', f'part{part}', f'{prompt_type}_prompt_{"with_img" if img else "without_img"}.txt')
        with open(prompt_path, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        logging.error(f"Prompt file not found: {prompt_path}")
        raise
    except Exception as e:
        logging.error(f"Error reading prompt file: {e}")
        raise

def load_part_model(part: int, img: bool) -> Type[BaseModel]:
    """
    Dynamically import Result model from specific part directory

    Returns:
        Optional[Type[BaseModel]]: Imported Pydantic model or None if import fails
    """
    # Construct the path to the Result.py file
    base_path = os.path.join('parts', f'part{part}')
    model_path = os.path.join(base_path, f'Result_{'with_img' if img else 'without_img'}.py')

    try:
        # Check if file exists
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")

        # Dynamically import the module
        spec = importlib.util.spec_from_file_location(f"part{part}_model", model_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Find and return the Result class
        part_result_class = getattr(module, 'Result', None)

        # Find and return the AI model version
        ai_model_ver = getattr(module, 'AI_MODEL_VER', '')

        # Find and return reasoning effort level
        reasoning_effort = getattr(module, 'REASONING_EFFORT', 'medium')

        if part_result_class is None:
            raise AttributeError(f"No Result class found in {model_path}")

        return part_result_class, ai_model_ver, reasoning_effort

    except (ImportError, FileNotFoundError, AttributeError) as e:
        print(f"Error importing model for part {part}: {e}")
        return None

def _generate_questions(part, level, img: bool, count, existing=None):
    try:
        # Load system and user prompts dynamically
        system_prompt = load_prompt(part, 'system', img)
        user_prompt = load_prompt(part, 'user', img)
        json_schema, ai_model_ver, reasoning_effort = load_part_model(part, img)

        # Format user prompt with actual values
        user_prompt = user_prompt.format(
            count=count,
            level=level,
            existing=existing if existing else 'none'
        )

        # print prompts for debugging
        logging.debug(f"System Prompt:\n{system_prompt}\n")
        logging.info(f"User Prompt:\n{user_prompt}\n")
        logging.info(f"AI model ver:{ai_model_ver}")
        logging.info(f"AI reasoning effort:{reasoning_effort}")

        response = client.responses.parse(
            model=ai_model_ver,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            reasoning={"effort": reasoning_effort},
            text_format=json_schema
        )

        logging.info(f"total tokens {response.usage.total_tokens}")
        parsed_response = response.output_parsed

        response_dict = parsed_response.model_dump()
        json_str = parsed_response.model_dump_json(indent=2)
        logging.info(f"dict result={json_str}")
        return response_dict['items']

    except Exception as e:
        logging.error(f"Error: {e}")
        return []

class ToeicQuestionGenerator:
    """Generates TOEIC questions based on specified parameters."""

    def __init__(self, part: int, level: int, img: bool):
        self.part = part
        self.level = level
        self.img = img
        self.verification_chain = self._setup_verification_chain()

    def _setup_verification_chain(self) -> VerificationChain:
        """
        Set up verification chain with consistent parameters
        """
        return (VerificationChain()
            .add_stage(replace_time_with_readable)
            .add_stage(verify_options)
            .add_stage(verify_speakers)
            .add_stage(verify_question_similarity)
            .add_stage(self.verify_cross_audio)
            .add_stage(self.verify_cross_img)
            .add_stage(stamping)
        )

    def verify_cross_audio(self, question: Dict, img: bool = False):
        if question['part'] not in (3,4) or not img:
            return VerifyStatus.UNVERIFIED, None

        logging.info("Verifying cross audio...")

        status, msg  = self._cross_verify(question, img=False)
        if status != VerifyStatus.UNVERIFIED:
            return VerifyStatus.FAIL_AUDIO_ANSWER_MATCH, f"Audio reveals answer: {msg}"
        return VerifyStatus.UNVERIFIED, msg


    def verify_cross_img(self, question: Dict, img: bool = False):
        if question['part'] not in (3,4) or not img:
            return VerifyStatus.UNVERIFIED, None

        logging.info("Verifying cross image...")

        status, msg = self._cross_verify(question, img=True)
        if status != VerifyStatus.UNVERIFIED:
            return VerifyStatus.FAIL_IMAGE_ANSWER_MATCH, f"Image reveals answer: {msg}"
        return VerifyStatus.UNVERIFIED, msg


    def _cross_verify(self, question: Dict, img: bool = False)-> Tuple[VerifyStatus, Optional[str]]:
        if not question['part'] in (3,4):
            return VerifyStatus.UNVERIFIED, None

        try:
            # Build the prompt based on part
            system_prompt = load_cross_prompt(question['part'], 'system', img)
            user_prompt = load_cross_prompt(question['part'], 'user', img)
            json_schema = load_cross_part_model(question['part'], img)
        except Exception as e:
            logging.error(f"Error loading prompts or models: {e}")
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
        logging.debug(f"System Prompt:\n{system_prompt}\n")
        logging.info(f"User Prompt:\n{user_prompt}\n")

        # Prepare messages
        user_message = [{"type": "input_text", "text": user_prompt}]

        try:
            response = client.responses.parse(
                model="gpt-5-mini-2025-08-07",
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                text_format=json_schema
            )
            logging.info(f"total tokens {response.usage.total_tokens}")
        except Exception as e:
            logging.error(f"OpenAI API error: {e}")
            return VerifyStatus.ERROR, f"OpenAI API error: {e}"

        parsed_response = response.output_parsed

        response_dict = parsed_response.model_dump()
        json_str = parsed_response.model_dump_json(indent=2)
        logging.info(f" AI dict result={json_str}")

        ai_answer = response_dict['answer']

        # convert answer dict to a 4 number vector e.g. {"A": xx,"B":yy,"C":zz,"D":ww} to [xx, yy, zz, ww]
        ai_vector = [ai_answer['A'], ai_answer['B'], ai_answer['C'], ai_answer.get('D', 0)]
        logging.info(f"ai_vector: {ai_vector}")
        logging.info(f"db_vector: {db_vector}")

        # check length match
        if len(db_vector) != len(ai_vector):
            print(f"  Length mismatch: db_vector has {len(db_vector)} options, v_ai has {len(ai_vector)} options")
            return VerifyStatus.ERROR, f"Answer option length mismatch"
        # compute sum of absolute difference
        diff = sum(abs(a - b) for a, b in zip(db_vector, ai_vector))
        logging.info(f"  Computed diff: {diff}")
        # threshold for acceptance is 10
        threshold = 70
        if diff < threshold:
            print(f"  Match detected (diff {diff} < {threshold})")
            return VerifyStatus.FAIL_AUDIO_ANSWER_MATCH, f"{ai_answer}"

        return VerifyStatus.UNVERIFIED, None

    def generate_questions(self, count: int, existing) -> List[Dict]:
        """Generate TOEIC questions."""
        print(f"existing questions: {existing}")
        # check part
        if self.part not in [1, 2, 3, 4]:
            raise ValueError("Invalid part number. Must be 1, 2, 3, or 4.")

        result = []
        if self.part == 1:
            for item in _generate_questions(self.part, self.level, self.img, count, existing=existing):
                q = {'part': 1, 'level': self.level, 'img_prompt': item['img_prompt']}
                q['A'] = item['A']
                q['B'] = item['B']
                q['C'] = item['C']
                q['D'] = item['D']
                q['answer'] = item['answer']
                q['type'] = item['type']
                q['valid'], q['valid_status'] = self.verification_chain.verify(q, self.img)
                result.append(q)

        elif self.part == 2:
            for item in _generate_questions(self.part, self.level, self.img, count, existing=existing):
                q = {'part': 2, 'level': self.level, 'img_prompt': None}
                q['A'] = item['A']
                q['B'] = item['B']
                q['C'] = item['C']
                q['D'] = None
                q['question'] = item ['question']
                q['answer'] = item['answer']
                q['valid'], q['valid_status'] = self.verification_chain.verify(q, self.img)
                result.append(q)

        elif self.part == 3:
            for item in _generate_questions(self.part, self.level, self.img, count, existing=existing):
                q = {'part': 3, 'level': self.level, 'img_prompt': None}
                if self.img:
                    q['img_prompt'] = item['img_prompt']
                q['prompt'] = json.dumps([conv["line"] for conv in item["script"]])
                q['sex'] = json.dumps([conv["speaker"] for conv in item["script"]])
                q['A'] = json.dumps([qu['A'] for qu in item['questions']])
                q['B'] = json.dumps([qu['B'] for qu in item['questions']])
                q['C'] = json.dumps([qu['C'] for qu in item['questions']])
                q['D'] = json.dumps([qu['D'] for qu in item['questions']])
                q['answer'] = json.dumps([qu['answer'] for qu in item['questions']])
                q['type'] = item['type']
                q['summary'] = item['summary']
                q['question'] = json.dumps([qu['question'] for qu in item['questions']])
                q['valid'], q['valid_status'] = self.verification_chain.verify(q, self.img)
                result.append(q)

        elif self.part == 4:
            for item in _generate_questions(self.part, self.level, self.img, count, existing=existing):
                q = {'part': 4, 'level': self.level, 'img_prompt': None}
                if self.img:
                    q['img_prompt'] = item['img_prompt']
                q['prompt'] = item['talk']
                q['sex'] = item['sex']
                q['A'] = json.dumps([qu['A'] for qu in item['questions']])
                q['B'] = json.dumps([qu['B'] for qu in item['questions']])
                q['C'] = json.dumps([qu['C'] for qu in item['questions']])
                q['D'] = json.dumps([qu['D'] for qu in item['questions']])
                q['answer'] = json.dumps([qu['answer'] for qu in item['questions']])
                q['type'] = item['type']
                q['summary'] = item['summary']
                q['question'] = json.dumps([qu['question'] for qu in item['questions']])
                q['valid'], q['valid_status'] = self.verification_chain.verify(q, self.img)
                result.append(q)

        return result

class DatabaseManager:
    """Manages SQLite database operations."""

    def __init__(self, db_path: str):
        """Initialize the database manager."""
        try:
            self.connection = sqlite3.connect(db_path)
            self.connection.row_factory = sqlite3.Row
            logging.debug(f"Connected to database: {db_path}")
        except sqlite3.Error as e:
            logging.error(f"Failed to connect to database: {e}")
            raise sqlite3.Error(f"Failed to connect to database: {e}")

    def insert_questions(self, part, level, questions: List[Dict]) -> int:
        """Insert questions into the database."""
        if not questions:
            logging.warning("No questions to insert")
            return 0

        cursor = self.connection.cursor()
        inserted_count = 0

        try:
            for question in questions:
                logging.debug(f"Inserting question: {question}")
                logging.debug(f"Types and value: " + ", ".join([f"{k}:{v}:{type(v)}" for k,v in question.items()]))

                cursor.execute(
                    """
                    INSERT INTO questions
                    (part, level, sex, question, prompt, answer, A, B, C, D, img_prompt, type, summary, topic, valid, valid_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        question.get("part"),
                        question.get("level"),
                        question.get("sex"),
                        question.get("question"),
                        question.get("prompt"),
                        question.get("answer"),
                        question.get("A"),
                        question.get("B"),
                        question.get("C"),
                        question.get("D"),
                        question.get("img_prompt"),
                        question.get("type"),
                        question.get("summary"),
                        question.get("topic"),
                        question.get("valid"),
                        question.get("valid_status")
                    )
                )
                inserted_count += 1

            self.connection.commit()
            logging.info(f"Successfully committed {inserted_count} questions to database")
        except sqlite3.Error as e:
            self.connection.rollback()
            logging.error(f"Failed to insert questions: {e}")
            raise sqlite3.Error(f"Failed to insert questions: {e}")
        finally:
            cursor.close()

        return inserted_count

    def load_questions_from_db(self, part: int, level: int) -> List[str]:
        """Load existing questions from the database for a specific part."""
        existing_questions = []

        cursor = self.connection.cursor()

        if part not in [1, 2, 3, 4]:
            logging.error("Invalid part number. Must be 1, 2, 3, or 4.")
            return existing_questions

        query = "SELECT * FROM questions WHERE part = ? AND level = ? AND valid = 0 ORDER BY id DESC LIMIT 100"

        try:
            cursor.execute(query, (part, level,))
            rows = cursor.fetchall()
            result = [dict(row) for row in rows]
        except sqlite3.Error as e:
            logging.error(f"Error loading questions from database: {e}")

        if part == 1:
            for q in result:
                existing_questions.append(q[q['answer']])
        elif part == 2:
            for q in result:
                existing_questions.append(q['question'])
        else: # part 3 and 4
            for q in result:
                existing_questions.append(q['summary'])

        return existing_questions

    def close(self) -> None:
        """Close the database connection."""
        if self.connection:
            self.connection.close()
            logging.info("Database connection closed")


def parse_arguments() -> argparse.Namespace:
    """Parse and validate command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate TOEIC questions and write to SQLite database"
    )

    parser.add_argument("--part", type=int, required=True, help="TOEIC part number")
    parser.add_argument("--level", type=int, required=True, help="Difficulty level")
    parser.add_argument("--img", action='store_true', help="With image prompt")
    parser.add_argument("--count", type=int, required=True, help="Number of questions to generate")
    parser.add_argument("--db", type=str, required=True, help="SQLite database file path")

    return parser.parse_args()


def validate_arguments(args: argparse.Namespace) -> bool:
    """Validate parsed arguments."""
    if args.part < 1:
        logging.error("--part must be a positive integer")
        return False
    if args.level < 1:
        logging.error("--level must be a positive integer")
        return False
    if args.count < 1:
        logging.error("--count must be a positive integer")
        return False
    if not args.db:
        logging.error("--db path cannot be empty")
        return False
    return True


def main():
    """Main function to orchestrate question generation and database insertion."""
    args = parse_arguments()

    # Setup logging before validation
    setup_logging()
    logging.info("=" * 80)
    logging.info("TOEIC Question Generator Started")
    logging.info("=" * 80)

    if not validate_arguments(args):
        logging.critical("Argument validation failed")
        sys.exit(1)

    try:
        db_manager = DatabaseManager(args.db)
        generator = ToeicQuestionGenerator(
            part=args.part,
            level=args.level,
            img=args.img
        )

        logging.info(f"Generating {args.count} TOEIC questions...")
        logging.info(f"  Part: {args.part}, Level: {args.level}")

        existing_questions = db_manager.load_questions_from_db(part=args.part, level=args.level)

        questions = generator.generate_questions(count=args.count, existing=existing_questions)

        if not questions:
            logging.error("No questions were generated")
            sys.exit(1)

        logging.info(f"Generated {len(questions)} questions successfully")

        # Log validation summary
        valid_count = sum(1 for q in questions if q.get('valid', -1) == 0)
        invalid_count = len(questions) - valid_count
        logging.info(f"Validation summary: {valid_count} valid, {invalid_count} invalid")

        logging.info("Writing to database...")

        inserted_count = db_manager.insert_questions(args.part, args.level, questions)
        logging.info(f"Successfully inserted {inserted_count} questions into database")
        logging.info(f"Database: {args.db}")
        logging.info("=" * 80)
        logging.info("TOEIC Question Generator Completed Successfully")
        logging.info("=" * 80)

        db_manager.close()

    except FileNotFoundError as e:
        logging.error(f"Database file not found - {e}")
        sys.exit(1)
    except sqlite3.Error as e:
        logging.error(f"Database error - {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error - {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
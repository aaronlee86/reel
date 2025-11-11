#!/usr/bin/env python3
"""
genToeicQ.py - TOEIC Question Generator
Generates TOEIC questions and writes them to a SQLite database.

Usage:
    python genToeicQ.py --part=1 --level=2 --accent=am --count=10 --db=sql.db
"""

import os
import argparse
import sqlite3
import sys
import json
import logging
from typing import List, Dict


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
from pydantic import BaseModel
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY")
)
logging.info("done")

ChatGPT_MODEL_VER = "gpt-5-mini-2025-08-07"



def _generate_part1_questions(level, count, existing=None):
    """Generate Part 1 questions with explanations"""
    class Result(BaseModel):
        picture_prompt: list[str]
        A: list[str]
        B: list[str]
        C: list[str]
        D: list[str]
        answer: list[str]
        explanation: list[str]
        topic: list[str]

    try:
        response = client.responses.parse(
            model=ChatGPT_MODEL_VER,
            input=[
                {"role": "system", "content": f"""Create mock TOEIC listening Part 1 questions: a picture and 4 statements.
                 Create the AI prompt to generate the picture as well. Randomize correct answer letters.
                 For each question, provide a clear explanation (2-3 sentences) of why the correct answer is right and why the other options are wrong.
                 Also assign a topic/category for each question (e.g., 'office', 'transportation', 'dining', 'outdoor activities', 'construction', 'shopping', 'healthcare', etc.).
                 Return arrays"""},
                {"role": "user", "content": f"""Generate {count} non-repetetive questions.
                 Avoid similar question from: {existing if existing else 'none'}.
                 Difficulty level: {level}/3. Return JSON arrays."""}
            ],
            text_format=Result
        )

        logging.info(f"total tokens {response.usage.total_tokens}")
        result = response.output_parsed
        logging.info(f"raw result={result}")

        result = dict(result)
        result = [dict(zip(result.keys(), values)) for values in zip(*result.values())]
        return result

    except Exception as e:
        logging.error(f"Error: {e}")
        return []

def _generate_part2_questions(level, count, existing=None):
    """Generate Part 2 questions with explanations"""
    class Result(BaseModel):
        question: list[str]
        A: list[str]
        B: list[str]
        C: list[str]
        answer: list[str]
        explanation: list[str]
        topic: list[str]

    try:
        response = client.responses.parse(
            model=ChatGPT_MODEL_VER,
            input=[
                {"role": "system", "content": f"""Create mock TOEIC listening Part 2 questions: a question or statement and 3 responses.
                 Randomize correct answer letters.
                 For each question, provide a clear explanation (2-3 sentences) of why the correct answer is the most appropriate response and why the other options are less suitable.
                 Also assign a topic/category for each question (e.g., 'business meeting', 'phone conversation', 'scheduling', 'requests', 'offers', 'opinions', 'daily routine', etc.).
                 Return arrays"""},
                {"role": "user", "content": f"""Generate {count} non-repetetive questions.
                 Avoid similar question from: {existing if existing else 'none'}.
                 Difficulty level: {level}/3. Return JSON arrays."""}
            ],
            text_format=Result
        )

        logging.info(f"total tokens {response.usage.total_tokens}")
        result = response.output_parsed
        logging.info(f"raw result={result}")

        result = dict(result)
        result = [dict(zip(result.keys(), values)) for values in zip(*result.values())]
        return result

    except Exception as e:
        logging.error(f"Error: {e}")
        return []

def _generate_part3_questions(level, count, existing=None):
    """Generate Part 3 questions with explanations"""
    class Result(BaseModel):
        reference_prompt: list[str]
        conv: list[list[str]]
        conv_sex: list[list[str]]
        conv_accent: list[list[str]]
        question_1: list[str]
        A1: list[str]
        B1: list[str]
        C1: list[str]
        D1: list[str]
        answer1: list[str]
        explanation1: list[str]
        question_2: list[str]
        A2: list[str]
        B2: list[str]
        C2: list[str]
        D2: list[str]
        answer2: list[str]
        explanation2: list[str]
        question_3: list[str]
        A3: list[str]
        B3: list[str]
        C3: list[str]
        D3: list[str]
        answer3: list[str]
        explanation3: list[str]
        summary: list[str]
        topic: list[str]

    try:
        response = client.responses.parse(
            model=ChatGPT_MODEL_VER,
            input=[
                {"role": "system", "content": f"""Create mock TOEIC listening Part 3 questions: conversations between 2-3 speakers (mix of genders) with 3 followed-up questions each.
                 Speaker's sex (man or woman) in conv_sex for each sentence. Speaker's accent (Am,Cn,Br,or Au) in conv_accent for each sentence.
                 Speakers of same sex must have different accent to differentiate.
                 The conversation should be 4–6 exchanges if 2 speakers; 6–8 exchanges if 3 speakers.
                 In returned conv array, don't need name or sex, only script.
                 The conversation may or may not refer to a chart or visual; if it does, also create the AI prompt to generate the reference (Chart or visual); if no reference, return empty string for the prompt.
                 In questions and options, if mentioning any speaker, speicify the gender (the man, men, woman, or women) but not accent.
                 For each of the 3 questions, provide a clear explanation (2-3 sentences) in explanation1, explanation2, and explanation3 fields of why the correct answer is right based on the conversation.
                 Also assign a topic/category for each conversation (e.g., 'travel planning', 'project discussion', 'customer service', 'job interview', 'office supplies', 'event planning', etc.).
                 A brief summary of the conversation within 20 words in 'summary' array.
                 Randomize correct answer letters.
                 Return arrays"""},
                {"role": "user", "content": f"""Generate {count} non-repetetive questions.
                 Avoid similar question from: {existing if existing else 'none'}.
                 Difficulty level: {level}/3. Return JSON arrays."""}
            ],
            text_format=Result
        )

        logging.info(f"total tokens {response.usage.total_tokens}")
        result = response.output_parsed
        logging.info(f"raw result={result}")

        result = dict(result)
        result = [dict(zip(result.keys(), values)) for values in zip(*result.values())]
        return result

    except Exception as e:
        logging.error(f"Error: {e}")
        return []

def _generate_part4_questions(level, count, existing=None):
    """Generate Part 4 questions with explanations"""
    class Result(BaseModel):
        reference_prompt: list[str]
        talk: list[str]
        question_1: list[str]
        type: list[str]
        A1: list[str]
        B1: list[str]
        C1: list[str]
        D1: list[str]
        answer1: list[str]
        explanation1: list[str]
        question_2: list[str]
        A2: list[str]
        B2: list[str]
        C2: list[str]
        D2: list[str]
        answer2: list[str]
        explanation2: list[str]
        question_3: list[str]
        A3: list[str]
        B3: list[str]
        C3: list[str]
        D3: list[str]
        answer3: list[str]
        explanation3: list[str]
        summary: list[str]
        topic: list[str]

    try:
        response = client.responses.parse(
            model=ChatGPT_MODEL_VER,
            input=[
                {"role": "system", "content": f"""Create mock TOEIC listening Part 4 questions: a monologue/talk (6-12 sentences) with 3 follow-up questions.
                                                    May include a visual reference (chart/table/schedule).
                                                    If it does, also create the AI prompt to generate the visual reference; if not, return empty string for the prompt.
                                                    Also return type of the talk (talk, announcement, advertisement, radio advertisement, news report, broadcast, tour, excerpt from a meeting, or message) in 'type' array.
                                                    For each of the 3 questions, provide a clear explanation (2-3 sentences) in explanation1, explanation2, and explanation3 fields of why the correct answer is right based on the talk.
                                                    Randomize correct answer letters.
                                                    Also assign a topic/category for each talk (e.g., 'product launch', 'weather forecast', 'museum tour', 'company policy', 'special offer', 'event announcement', etc.).
                                                    Also return a brief summary of the talk within 20 words in 'summary' array.
                                                    Return arrays"""},
                {"role": "user", "content": f"""Generate {count} non-repetetive questions.
                 Avoid similar question from: {existing if existing else 'none'}.
                 Difficulty level: {level}/3. Return JSON arrays."""
                 }
            ],
            text_format=Result,
            temperature=1
        )

        logging.info(f"total tokens {response.usage.total_tokens}")
        result = response.output_parsed
        logging.info(f"raw result={result}")

        result = dict(result)
        result = [dict(zip(result.keys(), values)) for values in zip(*result.values())]
        return result

    except Exception as e:
        logging.error(f"Error: {e}")
        return []


class ToeicQuestionGenerator:
    """Generates TOEIC questions based on specified parameters."""

    def __init__(self, part: int, level: int):
        self.part = part
        self.level = level

    def generate_questions(self, count: int, existing) -> List[Dict]:
        """Generate TOEIC questions."""
        print(f"existing questions: {existing}")
        # check part
        if self.part not in [1, 2, 3, 4]:
            raise ValueError("Invalid part number. Must be 1, 2, 3, or 4.")

        if self.part == 1:
            result = _generate_part1_questions(self.level, count, existing=existing)
            for q in result:
                q['img_prompt'] = q.pop('picture_prompt')
                q['part'] = 1
                q["level"] = self.level
                q['A'] = q.pop('A')
                q['B'] = q.pop('B')
                q['C'] = q.pop('C')
                q['D'] = q.pop('D')
                q['answer'] = q.pop('answer')
                q['explanation'] = q.pop('explanation')

        elif self.part == 2:
            result = _generate_part2_questions(self.level, count, existing=existing)
            for q in result:
                q['part'] = 2
                q["level"] = self.level
                q['A'] = q.pop('A')
                q['B'] = q.pop('B')
                q['C'] = q.pop('C')
                q['answer'] = q.pop('answer')
                q['explanation'] = q.pop('explanation')

        elif self.part == 3:
            result = _generate_part3_questions(self.level, count, existing=existing)
            for q in result:
                q['img_prompt'] = q.pop('reference_prompt')
                q['prompt'] = json.dumps(q.pop('conv'))
                q['part'] = 3
                q["level"] = self.level
                q['A'] = json.dumps([q.pop('A1'), q.pop('A2'), q.pop('A3')])
                q['B'] = json.dumps([q.pop('B1'), q.pop('B2'), q.pop('B3')])
                q['C'] = json.dumps([q.pop('C1'), q.pop('C2'), q.pop('C3')])
                q['D'] = json.dumps([q.pop('D1'), q.pop('D2'), q.pop('D3')])
                q['answer'] = json.dumps([q.pop('answer1'), q.pop('answer2'), q.pop('answer3')])
                q['question'] = json.dumps([q.pop('question_1'), q.pop('question_2'), q.pop('question_3')])
                q['explanation'] = json.dumps([q.pop('explanation1'), q.pop('explanation2'), q.pop('explanation3')])
                q['sex'] = json.dumps(q.pop('conv_sex'))
                q['accent'] = json.dumps(q.pop('conv_accent'))
        elif self.part == 4:
            result = _generate_part4_questions(self.level, count, existing=existing)
            for q in result:
                q['img_prompt'] = q.pop('reference_prompt')
                q['prompt'] = json.dumps(q.pop('talk'))
                q['part'] = 4
                q["level"] = self.level
                q['A'] = json.dumps([q.pop('A1'), q.pop('A2'), q.pop('A3')])
                q['B'] = json.dumps([q.pop('B1'), q.pop('B2'), q.pop('B3')])
                q['C'] = json.dumps([q.pop('C1'), q.pop('C2'), q.pop('C3')])
                q['D'] = json.dumps([q.pop('D1'), q.pop('D2'), q.pop('D3')])
                q['answer'] = json.dumps([q.pop('answer1'), q.pop('answer2'), q.pop('answer3')])
                q['question'] = json.dumps([q.pop('question_1'), q.pop('question_2'), q.pop('question_3')])
                q['explanation'] = json.dumps([q.pop('explanation1'), q.pop('explanation2'), q.pop('explanation3')])

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
                    (part, level, accent, sex, question, prompt, answer, A, B, C, D, img_prompt, type, summary, explanation, topic)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        question.get("part"),
                        question.get("level"),
                        question.get("accent"),
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
                        question.get("explanation"),
                        question.get("topic")
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

        query = "SELECT * FROM questions WHERE part = ? AND level = ? ORDER BY id DESC LIMIT 100"

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
            level=args.level
        )

        logging.info(f"Generating {args.count} TOEIC questions...")
        logging.info(f"  Part: {args.part}, Level: {args.level}")

        existing_questions = db_manager.load_questions_from_db(part=args.part, level=args.level)

        questions = generator.generate_questions(count=args.count, existing=existing_questions)

        if not questions:
            logging.error("No questions were generated")
            sys.exit(1)

        logging.info(f"Generated {len(questions)} questions successfully")
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
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
import random
import json
from typing import List, Dict


# Initialize the OpenAI client with API key from environment variable
print("loading OpenAI module...")
from openai import OpenAI
from pydantic import BaseModel
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY")
)
print("done")

ChatGPT_MODEL_VER = "gpt-5-mini-2025-08-07"

temp_result= {'reference_prompt': ['Create a clear table titled "Q3 Marketing Metrics by Channel and Region" with columns: Channel, Region, Q3 Spend, Store Visits Change (%), Conversion Rate (%), Note. Include rows showing: Digital (National) Q3 Spend $450,000, Store Visits Change +5%, Conversion Rate 3.4%, Note: digital outperforms print by ~30%; Print (Midwest) Q3 Spend $120,000, Store Visits Change +12%, Conversion Rate 1.8%, Note: coupon program dependent on vendor rebate; indicate a coupon budget row with a flag that the coupon assumption depends on a vendor rebate that is not guaranteed. Format so the listener could refer to differences between digital and print and the rebate dependency.', '', '', ''], 'conversation': [['I think reallocating funds from print ads to social media will hit the engagement targets faster.', 'The third quarter numbers already show digital channels outperform print by almost thirty percent.', "That's true but print still drives store traffic in rural regions according to the spreadsheet.", 'Right the spreadsheet shows store visits up in Q3 in the Midwest, but digital conversions are higher overall.', "If we cut print by fifteen percent and add that to paid search we'll still cover regional coupons.", "We need to be careful the spreadsheet's coupon budget assumption depends on a vendor rebate that isn't guaranteed.", 'If the rebate falls through we can pause the regional coupon program and redirect funds into retargeting.', 'I worry about pausing coupons during the holiday promotion the table projects a five percent sales drop without them.', 'What if we run a short coupon pilot in the key stores and use the remaining funds for a targeted retargeting campaign?', 'That could give us the data to decide in time for the holiday push.'], ['We have to take Line B offline next week for the bearing replacement.', 'If we shut it down for two days we can get the warranty-covered parts installed by our OEM technician.', 'The local contractor quoted a faster turnaround but their quote excludes parts.', 'Faster could mean less lost production but we risk paying out of pocket for parts that might be covered by the warranty.', "Can we confirm coverage before committing If the OEM's schedule slips we'll be forced into the contractor anyway.", "I can expedite delivery of the noncovered parts so labor isn't idle if the OEM cancels.", 'That would mean we absorb parts cost but keep the line downtime down to a single shift.', 'I prefer minimizing cost variance in this quarter absorbing the parts cost would hurt the budget.', 'What about a compromise have the contractor stand by and order parts on hold pending OEM confirmation?'], ['You did a solid job leading the East account this year.', 'Thanks I exceeded the retention targets by four percent and brought on two major clients.', 'Still the budget for raises is tight we need to justify the increase to finance with quantifiable metrics.', "I have the client revenue breakdown and the retention rates but there are onboarding cost variances we couldn't control.", "If you can show net margin improvement after onboarding I'm more likely to push for at least a midrange raise.", "I'll assemble a concise packet with margin calculations and client growth projections by Friday.", 'Do that and also include a brief client testimonial it helps persuade senior management.', "Got it I'll prioritize the numbers and the testimonial."], ['I need to change my flight because the client meeting moved up by a day.', 'The corporate policy requires booking the lowest logical fare but allows exceptions with manager approval.', 'If you change to the earlier flight the refundable fare is higher but we can file for an exception if you document the client request.', 'I can get an email from the client confirming the date will that be enough?', "Yes that should satisfy audit but make sure you note the times to show it's the only reasonable connection.", 'Also check seating availability the afternoon flights are full so moving earlier means limited aisle seats.', 'Aisle seat is important because I carry presentation materials can we request one when we submit the form?', "You can add a seat preference but it's not guaranteed under lowest fare exceptions.", "If you can't get an aisle we might cover a seat upgrade if the client's confirmation explicitly states an earlier arrival is critical.", "I'll get the client's email and then decide whether to request approval for the refundable fare or risk a nonrefundable change."]], 'conversation_sex': [['man', 'woman', 'man', 'woman', 'man', 'woman', 'man', 'woman', 'man', 'woman'], ['man', 'woman', 'man', 'man', 'woman', 'man', 'man', 'woman', 'man'], ['woman', 'man', 'woman', 'man', 'woman', 'man', 'woman', 'man'], ['man', 'woman', 'woman', 'man', 'woman', 'woman', 'man', 'woman', 'woman', 'man']], 
              'conversation_accent': [['Am', 'Br', 'Am', 'Br', 'Am', 'Br', 'Am', 'Br', 'Am', 'Br'], ['Au', 'Am', 'Cn', 'Au', 'Am', 'Cn', 'Au', 'Am', 'Cn'], ['Am', 'Br', 'Am', 'Br', 'Am', 'Br', 'Am', 'Br'], ['Am', 'Cn', 'Br', 'Am', 'Cn', 'Br', 'Am', 'Cn', 'Br', 'Am']], 'question_1': ['What is the primary issue the speakers are trying to resolve?', 'What decision do the speakers need to make about Line B?', "What is the woman's main concern about approving a raise?", 'Why might the company approve the higher refundable fare for the man?'], 
              'A1': ['Whether to reallocate marketing funds from print to digital because digital metrics are stronger.', 'Whether to replace the bearings immediately with the local contractor without confirming warranty coverage.', "That the employee's interpersonal skills need improvement before any raise is considered.", 'Because the refundable fare includes a seat upgrade the company prefers to pay for comfort.'],
              'B1': ['How to increase print ad spend to boost store visits in rural regions.', 'Whether to cancel Line B permanently and replace it with a different line.', 'That raises are distributed equally regardless of individual performance.', 'Because the man prefers an aisle seat and the company always pays for preferred seating.'],
              'C1': ['Which vendor will supply the coupons for the holiday program.', 'Whether to wait for the OEM technician and use warranty-covered parts despite longer downtime or hire the contractor for a faster fix but pay for parts.', 'That the man should be transferred to a different account before receiving a raise.', 'Because the man booked the refundable fare originally and policy requires reimbursement of original tickets.'],
              'D1': ['If they should eliminate the coupon program entirely to save budget.', 'Whether to convert the repair into a capital expenditure this quarter.', 'That senior management is opposed to any raises this year.', 'Because the company wants to avoid documenting any client-related exceptions.'],
              'answer1': ['A', 'C', 'A', 'C'], 'question_2': ['Why does the woman urge caution about cutting print in the marketing plan?', 'Why does the woman (the manager) prefer not to absorb the parts cost for the repair?', 'What will the man prepare to support his request for a raise?', 'What additional action must the man take to strengthen his exception request for the flight change?'], 'A2': ['Because print is the cheapest channel and reallocating would exceed the overall budget.', 'Because she wants to minimize cost variance in this quarter which would be hurt by absorbing parts costs.', 'A list of team members and their weekly hours to justify headcount.', 'Buy the refundable fare immediately before getting client confirmation.'], 'B2': ['Because the woman prefers long-term contracts with print vendors.', "Because warranty-covered repairs would increase downtime beyond the quarter's schedule.", 'A narrative report describing his leadership style without numbers.', 'Send a travel request without any supporting documentation and then follow up.'], 'C2': ["Because the spreadsheet's coupon budget assumption depends on a vendor rebate that may not materialize.", 'Because the contractor will do a better job than the OEM technician.', 'A concise packet with margin calculations client growth projections and a client testimonial.', 'Request a seat preference after the change is approved and hope for the best.'], 'D2': ['Because digital channels cannot be measured reliably in Q3.', 'Because the parts are impossible to source locally.', 'Only anecdotal client comments without financial figures.', 'Call the airline and ask them to waive the fare difference verbally.'], 'answer2': ['C', 'B', 'C', 'C'], 'question_3': ['What compromise does the man propose to reduce the risk if the vendor rebate fails?', 'What compromise do the speakers suggest to balance downtime and cost if OEM scheduling is uncertain?', "Which tone best describes the woman's attitude toward the raise request?", 'Under what condition might the company agree to pay for a seat upgrade?'], 'A3': ['Pause all promotions and move all spend to social media immediately.', 'Have the contractor stand by and order parts on hold pending OEM confirmation.', 'Dismissive and uninterested refusing to help with documentation.', 'If the man personally pays the difference and keeps the receipt.'], 'B3': ['Double the coupon budget to offset any sales losses during the holiday.', 'Cancel the warranty claim and do all repairs in-house regardless of cost.', 'Neutral and detached offering no clear guidance.', 'If the man books an additional return flight at his expense.'], 'C3': ['Run a short coupon pilot in key stores and use remaining funds for targeted retargeting to gather data before the holiday.', 'Proceed immediately with the contractor and accept the parts cost as a sunk expense.', 'Supportive but cautious requiring quantifiable evidence to persuade finance.', 'If the client confirmation explicitly states that arriving earlier is critical and documents the necessity.'],
              'D3': ['Shift all coupon funds to vendor rebates and hope the rebate is approved.', 'Delay all maintenance until next quarter to avoid immediate costs.', 'Hostile and uncooperative refusing to sign off on any raises.', 'If the man chooses a more expensive airline preferred by management.'],
              'answer3': ['C', 'A', 'C', 'C']}

def tmp_generate_part3_questions(level, count):
    result = temp_result
    result = [dict(zip(result.keys(), values)) for values in zip(*result.values())]
    print(f"new result={result}")
    return result

def _generate_part1_questions(level, count):
    """Translate Chinese to colloquial American English"""
    class Result(BaseModel):
        picture_prompt: list[str]
        A: list[str]
        B: list[str]
        C: list[str]
        D: list[str]
        answer: list[str]

    try:
        response = client.responses.parse(
            model=ChatGPT_MODEL_VER,
            input=[
                {"role": "system", "content": f"""Create mock TOEIC listening part 1 questions: a picture and 4 statements.
                 Create the AI prompt to generate the picture as well.
                 return arrays"""},
                {"role": "user", "content": f"make {count} non-repetetive questions, difficulty level is {level} out of 5. return arrays."}
            ],
            text_format=Result
        )

        print(f"total tokens {response.usage.total_tokens}")
        result = response.output_parsed

        result = dict(result)
        result = [dict(zip(result.keys(), values)) for values in zip(*result.values())]
        return result

    except Exception as e:
        print(f"Error: {e}")
        return []
    
def _generate_part2_questions(level, count):
    """Translate Chinese to colloquial American English"""
    class Result(BaseModel):
        question: list[str]
        A: list[str]
        B: list[str]
        C: list[str]
        answer: list[str]

    try:
        response = client.responses.parse(
            model=ChatGPT_MODEL_VER,
            input=[
                {"role": "system", "content": f"""Create mock realistic TOEIC-style listening part 2 questions: a question or statement and 3 responses.
                 return arrays"""},
                {"role": "user", "content": f"make {count} non-repetetive questions, difficulty level is {level} out of 5. return arrays."}
            ],
            text_format=Result
        )

        print(f"total tokens {response.usage.total_tokens}")
        result = response.output_parsed

        result = dict(result)
        result = [dict(zip(result.keys(), values)) for values in zip(*result.values())]
        return result

    except Exception as e:
        print(f"Error: {e}")
        return []

def _generate_part3_questions(level, count):
    """Translate Chinese to colloquial American English"""
    class Result(BaseModel):
        reference_prompt: list[str]
        conversation: list[list[str]]
        conversation_sex: list[list[str]]
        conversation_accent: list[list[str]]
        question_1: list[str]
        A1: list[str]
        B1: list[str]
        C1: list[str]
        D1: list[str]
        answer1: list[str]
        question_2: list[str]
        A2: list[str]
        B2: list[str]
        C2: list[str]
        D2: list[str]
        answer2: list[str]
        question_3: list[str]
        A3: list[str]
        B3: list[str]
        C3: list[str]
        D3: list[str]
        answer3: list[str]

    try:
        response = client.responses.parse(
            model=ChatGPT_MODEL_VER,
            input=[
                {"role": "system", "content": f"""Create mock TOEIC listening part 3 questions: a conversation between 2 or 3 people (at least one man and one woman for most cases. 8% of chance it might be 2 men or 2 women) and 3 followed-up questions.
                 Speaker's sex (man or woman) in conversation_sex for each sentence. Speaker's accent (Am,Cn,Br,or Au) in conversaction_accent for each sentence.
                 Speakers of same sex must have different accent to differentiate.
                 The conversation should be 4–6 exchanges if 2 speakers; 6–8 exchanges if 3 speakers.
                 realistic and relevant to business contexts.
                 In returned conversation array, don't use dash and don't need name or sex, only script. 
                 The conversation may or may not refer to a chart or visual; if it does, also create the AI prompt to generate the reference (Chart or visual).
                 In questions and options, if mentioning any speaker, speicify the gender (the man, men, woman, or women) but not accent.
                 return arrays"""},
                {"role": "user", "content": f"make {count} non-repetetive questions, difficulty level is {level} out of 5. return arrays."}
            ],
            text_format=Result
        )

        print(f"total tokens {response.usage.total_tokens}")
        result = response.output_parsed

        result = dict(result)
        result = [dict(zip(result.keys(), values)) for values in zip(*result.values())]
        return result

    except Exception as e:
        print(f"Error: {e}")
        return []
    
def _generate_part4_questions(level, count):
    """Translate Chinese to colloquial American English"""
    class Result(BaseModel):
        reference_prompt: list[str]
        talk: list[str]
        question_1: list[str]
        A1: list[str]
        B1: list[str]
        C1: list[str]
        D1: list[str]
        answer1: list[str]
        question_2: list[str]
        A2: list[str]
        B2: list[str]
        C2: list[str]
        D2: list[str]
        answer2: list[str]
        question_3: list[str]
        A3: list[str]
        B3: list[str]
        C3: list[str]
        D3: list[str]
        answer3: list[str]

    try:
        response = client.responses.parse(
            model=ChatGPT_MODEL_VER,
            input=[
                {"role": "system", "content": f"""Create mock realistic TOEIC-style listening part 4 questions: a talk given by a personl and 3 followed-up questions.
                 The talk should contain 6 to 12 sentences.
                 The question may or may not contain a chart, table, or schedule; if it does, also create the AI prompt to generate the reference (Chart, table, or schedule).
                 return arrays"""},
                {"role": "user", "content": f"make me {count} non-repetetive questions, difficulty level is {level} out of 5. return arrays."}
            ],
            text_format=Result
        )

        print(f"total tokens {response.usage.total_tokens}")
        result = response.output_parsed

        result = dict(result)
        result = [dict(zip(result.keys(), values)) for values in zip(*result.values())]
        return result

    except Exception as e:
        print(f"Error: {e}")
        return []
    

class ToeicQuestionGenerator:
    """Generates TOEIC questions based on specified parameters."""
    
    def __init__(self, part: int, level: int, accent: str):
        self.part = part
        self.level = level
        self.accent = accent
    
    def generate_questions(self, count: int) -> List[Dict]:
        """Generate TOEIC questions."""
        # check part
        if self.part not in [1, 2, 3, 4]:
            raise ValueError("Invalid part number. Must be 1, 2, 3, or 4.")
        
        if self.part == 1:
            result = _generate_part1_questions(self.level, count)
            for q in result:
                q['img_prompt'] = q.pop('picture_prompt')
                q['part'] = 1
                q["level"] = self.level
                q['A'] = q.pop('A')
                q['B'] = q.pop('B')
                q['C'] = q.pop('C')
                q['D'] = q.pop('D')
                q['answer'] = q.pop('answer')
                
        elif self.part == 2:
            result = _generate_part2_questions(self.level, count)
            for q in result:
                q['part'] = 2
                q["level"] = self.level
                q['A'] = q.pop('A')
                q['B'] = q.pop('B')
                q['C'] = q.pop('C')
                q['answer'] = q.pop('answer')
            
        elif self.part == 3:
            result = _generate_part3_questions(self.level, count)
            for q in result:
                q['img_prompt'] = q.pop('reference_prompt')
                q['prompt'] = json.dumps(q.pop('conversation'))
                q['part'] = 3
                q["level"] = self.level
                q['A'] = json.dumps([q.pop('A1'), q.pop('A2'), q.pop('A3')])
                q['B'] = json.dumps([q.pop('B1'), q.pop('B2'), q.pop('B3')])
                q['C'] = json.dumps([q.pop('C1'), q.pop('C2'), q.pop('C3')])
                q['D'] = json.dumps([q.pop('D1'), q.pop('D2'), q.pop('D3')])
                q['answer'] = json.dumps([q.pop('answer1'), q.pop('answer2'), q.pop('answer3')])
                q['question'] = json.dumps([q.pop('question_1'), q.pop('question_2'), q.pop('question_3')])
                q['sex'] = json.dumps(q.pop('conversation_sex'))
                q['accent'] = json.dumps(q.pop('conversation_accent'))
        elif self.part == 4:
            result = _generate_part4_questions(self.level, count)
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

        return result

class DatabaseManager:
    """Manages SQLite database operations."""
    
    def __init__(self, db_path: str):
        """Initialize the database manager."""
        try:
            self.connection = sqlite3.connect(db_path)
            self.connection.row_factory = sqlite3.Row
        except sqlite3.Error as e:
            raise sqlite3.Error(f"Failed to connect to database: {e}")
    
    def insert_questions(self, part, level, questions: List[Dict]) -> int:
        """Insert questions into the database."""
        if not questions:
            return 0
        
        cursor = self.connection.cursor()
        inserted_count = 0
        
        try:
            for question in questions:
                print(f"Inserting question: {question}")

                cursor.execute(
                    """
                    INSERT INTO questions 
                    (part, level, accent, sex, used, question, prompt, answer, A, B, C, D, img_prompt)
                    VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        question.get("img_prompt")
                    )
                )
                inserted_count += 1
            
            self.connection.commit()
        except sqlite3.Error as e:
            self.connection.rollback()
            raise sqlite3.Error(f"Failed to insert questions: {e}")
        finally:
            cursor.close()
        
        return inserted_count
    
    def close(self) -> None:
        """Close the database connection."""
        if self.connection:
            self.connection.close()


def parse_arguments() -> argparse.Namespace:
    """Parse and validate command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate TOEIC questions and write to SQLite database"
    )
    
    parser.add_argument("--part", type=int, required=True, help="TOEIC part number")
    parser.add_argument("--level", type=int, required=True, help="Difficulty level")
    parser.add_argument("--accent", type=str, required=True, help="Accent type (e.g., 'am')")
    parser.add_argument("--count", type=int, required=True, help="Number of questions to generate")
    parser.add_argument("--db", type=str, required=True, help="SQLite database file path")
    
    return parser.parse_args()


def validate_arguments(args: argparse.Namespace) -> bool:
    """Validate parsed arguments."""
    if args.part < 1:
        print("Error: --part must be a positive integer", file=sys.stderr)
        return False
    if args.level < 1:
        print("Error: --level must be a positive integer", file=sys.stderr)
        return False
    if args.count < 1:
        print("Error: --count must be a positive integer", file=sys.stderr)
        return False
    if not args.db:
        print("Error: --db path cannot be empty", file=sys.stderr)
        return False
    return True


def main():
    """Main function to orchestrate question generation and database insertion."""
    args = parse_arguments()
    
    if not validate_arguments(args):
        sys.exit(1)
    
    try:
        db_manager = DatabaseManager(args.db)
        generator = ToeicQuestionGenerator(
            part=args.part,
            level=args.level,
            accent=args.accent
        )
        
        print(f"Generating {args.count} TOEIC questions...")
        print(f"  Part: {args.part}, Level: {args.level}, Accent: {args.accent}")
        
        questions = generator.generate_questions(count=args.count)
        
        if not questions:
            print("Error: No questions were generated", file=sys.stderr)
            sys.exit(1)
        
        print(f"Generated {len(questions)} questions successfully")
        print("Writing to database...")
        
        inserted_count = db_manager.insert_questions(args.part, args.level, questions)
        print(f"Successfully inserted {inserted_count} questions into database")
        print(f"Database: {args.db}")
        
        db_manager.close()
    
    except FileNotFoundError as e:
        print(f"Error: Database file not found - {e}", file=sys.stderr)
        sys.exit(1)
    except sqlite3.Error as e:
        print(f"Error: Database error - {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

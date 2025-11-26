 # --- ENUMS -------------------------------------------------------
from enum import Enum
from pydantic import BaseModel, Field
from typing import List

class SpeakerEnum(str, Enum):
    man1 = "man1"
    woman1 = "woman1"
    man2 = "man2"
    woman2 = "woman2"

class AnswerEnum(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"

# --- INNER OBJECTS ----------------------------------------------

class ScriptLine(BaseModel):
    speaker: SpeakerEnum
    line: str

class Question(BaseModel):
    question: str
    answer: AnswerEnum
    A: str
    B: str
    C: str
    D: str

# --- TOEIC PART 3 OBJECT ----------------------------------------

class ToeicPart3(BaseModel):
    script: List[ScriptLine]
    questions: List[Question] = Field(..., min_length=3, max_length=3)
    summary: str

    model_config = {
        "extra": "forbid"   # additionalProperties: false
    }

# --- ARRAY OF TOEIC PART 3 --------------------------------------

class Result(BaseModel):
    """
    Top-level object for response_format.schema.
    The API will return: { "items": [ ToeicPart3, ToeicPart3, ... ] }
    """
    items: List[ToeicPart3]

    model_config = {
        "extra": "forbid"  # no extra fields
    }

AI_MODEL_VER = "gpt-5-mini-2025-08-07"
REASONING_EFFORT = "medium"
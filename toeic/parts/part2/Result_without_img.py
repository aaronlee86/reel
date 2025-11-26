from typing import List, Literal
from pydantic import BaseModel, Field


class Question(BaseModel):
    question: str
    answer: Literal["A", "B", "C"]
    A: str
    B: str
    C: str

    model_config = {
        "extra": "forbid"  # no unexpected fields allowed
    }


class Result(BaseModel):
    items: List[Question]

    model_config = {
        "extra": "forbid"
    }

AI_MODEL_VER = "gpt-5-mini-2025-08-07"
REASONING_EFFORT = "medium"
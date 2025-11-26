from typing import Optional, List, Literal
from pydantic import BaseModel, Field

class Question(BaseModel):
    question: str
    answer: Literal["A", "B", "C", "D"]
    A: str
    B: str
    C: str
    D: str

    model_config = {
        "extra": "forbid"  # additionalProperties: false
    }

class TalkItem(BaseModel):
    talk: str
    sex: Optional[Literal["man", "woman"]] = None
    questions: List[Question] = Field(min_length=3, max_length=3)
    type: Literal[
        "talk",
        "announcement",
        "advertisement",
        "news report",
        "broadcast",
        "tour",
        "excerpt from a meeting",
        "phone message",
        "message"
    ]
    summary: str

    model_config = {
        "extra": "forbid"  # additionalProperties: false
    }


class Result(BaseModel):
    items: List[TalkItem]

    model_config = {
        "extra": "forbid"  # additionalProperties: false
    }

AI_MODEL_VER = "gpt-5-mini-2025-08-07"
REASONING_EFFORT = "medium"
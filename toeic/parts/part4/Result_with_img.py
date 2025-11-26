from typing import Optional, List, Literal
from pydantic import BaseModel, Field
import os, sys

# Get the directory of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Add the directory to sys.path
sys.path.insert(0, current_dir)

from Result_without_img import Question

class TalkItem(BaseModel):
    talk: str
    sex: Optional[Literal["man", "woman"]] = None
    img_prompt: str
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

AI_MODEL_VER = "gpt-5.1-2025-11-13"
REASONING_EFFORT = "high"
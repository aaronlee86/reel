 # --- ENUMS -------------------------------------------------------
from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Literal
import os, sys

# Get the directory of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Add the directory to sys.path
sys.path.insert(0, current_dir)

from Result_without_img import ScriptLine, Question

class ToeicPart3(BaseModel):
    script: List[ScriptLine]
    img_prompt: str
    questions: List[Question] = Field(..., min_length=3, max_length=3)
    summary: str
    type: Literal["Office", "CustomerService", "Other"]

    model_config = {
        "extra": "forbid"   # additionalProperties: false
    }

class Result(BaseModel):
    items: List[ToeicPart3]

    model_config = {
        "extra": "forbid"  # no extra fields
    }

AI_MODEL_VER = "gpt-5.1-2025-11-13"
REASONING_EFFORT = "high"
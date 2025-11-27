from pydantic import BaseModel, Field
from typing import List


class AnswerScore(BaseModel):
    A: float = Field(..., ge=0, le=100)
    B: float = Field(..., ge=0, le=100)
    C: float = Field(..., ge=0, le=100)
    D: float = Field(..., ge=0, le=100)
    explain_A: str
    explain_B: str
    explain_C: str
    explain_D: str

    model_config = {
        "extra": "forbid"  # additionalProperties: false
    }


class Result(BaseModel):
    answer: AnswerScore

    model_config = {
        "extra": "forbid"  # top-level additionalProperties: false
    }

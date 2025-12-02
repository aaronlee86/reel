from enum import IntEnum
from typing import Callable, Dict, List, Optional, Tuple

class VerifyStatus(IntEnum):
    UNVERIFIED = 0
    VALID = 1
    ERROR = 2
    FAIL_SIMILAR_QUESTION = 3
    FAIL_ANSWER_CHAR = 4
    FAIL_AUDIO_ANSWER_MATCH = 5
    FAIL_IMAGE_ANSWER_MATCH = 6
    FAIL_MORE_THAN_3_PEOPLE = 7
    FAIL_ANSWER_MISMATCH = 8
    FAIL_SPEAKER_NAMING = 9


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
                if status != VerifyStatus.VALID and status != VerifyStatus.UNVERIFIED:
                    return status, message
            except Exception as e:
                return VerifyStatus.ERROR, f"Exception in verification function {stage.__name__}: {e}"

        # If all stages pass
        return status, message
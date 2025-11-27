from enum import IntEnum

class VerifyStatus(IntEnum):
    UNVERIFIED = 0
    VALID = 1
    FAIL_SIMILAR_QUESTION = 2
    INVALID = 3
    ERROR = 4
    FAIL_AUDIO_ANSWER_MATCH = 5
    FAIL_IMAGE_ANSWER_MATCH = 6


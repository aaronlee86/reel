from enum import IntEnum

class VerifyStatus(IntEnum):
    UNVERIFIED = 0
    VALID = 1
    PREVALID_FAIL = 2
    INVALID = 3
    ERROR = 4

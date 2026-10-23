from typing import Any, Optional, Dict
from fastapi import HTTPException


class IncuBrixError(Exception):
    """
    Standard IncuBrix Structured Error format:
    {"error": {"code": str, "message": str, "retryable": bool, "details": any}}
    """
    def __init__(
        self,
        code: str,
        message: str,
        retryable: bool = False,
        details: Optional[Any] = None,
        status_code: int = 400
    ):
        self.code = code
        self.message = message
        self.retryable = retryable
        self.details = details
        self.status_code = status_code
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "retryable": self.retryable,
                "details": self.details
            }
        }


# Documented Error Codes
ERR_INVALID_DURATION = "INVALID_DURATION"
ERR_INVALID_SECTIONS = "INVALID_SECTIONS"
ERR_INVALID_PROMPT = "INVALID_PROMPT"
ERR_COPYRIGHT_RESTRICTION = "COPYRIGHT_RESTRICTION"
ERR_JOB_NOT_FOUND = "JOB_NOT_FOUND"
ERR_IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
ERR_INVALID_STEM = "INVALID_STEM"
ERR_NARRATION_ERROR = "NARRATION_ERROR"
ERR_PROVIDER_ERROR = "PROVIDER_ERROR"
ERR_AUDIO_PROCESSING_ERROR = "AUDIO_PROCESSING_ERROR"
ERR_STORAGE_ERROR = "STORAGE_ERROR"
ERR_INTERNAL_ERROR = "INTERNAL_SERVER_ERROR"

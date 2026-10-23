import json
import logging
import sys
from datetime import datetime, timezone
from contextvars import ContextVar
from typing import Optional

# Context variables for request tracing and job association
correlation_id_ctx: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)
job_id_ctx: ContextVar[Optional[str]] = ContextVar("job_id", default=None)


class JSONFormatter(logging.Formatter):
    """
    Structured JSON formatter ensuring logs contain:
    - timestamp (ISO-8601 UTC)
    - level
    - message
    - job_id
    - correlation_id
    - logger / module
    """
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "line": record.lineno,
            "job_id": getattr(record, "job_id", None) or job_id_ctx.get(),
            "correlation_id": getattr(record, "correlation_id", None) or correlation_id_ctx.get(),
        }

        # Include exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Include any extra custom metadata passed
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            log_entry["data"] = record.extra_data

        return json.dumps(log_entry, default=str)


def setup_logging(level: str = "INFO"):
    root_logger = logging.getLogger()
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)

    # Avoid adding duplicate handlers if already configured
    if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        root_logger.addHandler(handler)
    else:
        for handler in root_logger.handlers:
            handler.setFormatter(JSONFormatter())

    # Suppress overly chatty 3rd-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("multipart").setLevel(logging.WARNING)

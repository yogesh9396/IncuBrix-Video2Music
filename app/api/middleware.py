import uuid
import logging
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from app.models.errors import IncuBrixError, ERR_INTERNAL_ERROR, ERR_INVALID_DURATION, ERR_INVALID_SECTIONS
from app.logging_config import correlation_id_ctx

logger = logging.getLogger(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        corr_id = request.headers.get("X-Correlation-Id", str(uuid.uuid4()))
        correlation_id_ctx.set(corr_id)
        response = await call_next(request)
        response.headers["X-Correlation-Id"] = corr_id
        return response


async def incubrix_exception_handler(request: Request, exc: IncuBrixError) -> JSONResponse:
    logger.warning(f"IncuBrixError [{exc.code}]: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    first_err = errors[0] if errors else {}
    loc = ".".join(str(l) for l in first_err.get("loc", []))
    msg = first_err.get("msg", "Invalid request body")
    
    # Map common validation errors to specific documented codes
    code = "INVALID_REQUEST"
    if "section" in msg.lower() or "sections" in loc:
        code = ERR_INVALID_SECTIONS
    elif "duration_s" in loc or "duration" in msg.lower():
        code = ERR_INVALID_DURATION

    # Ensure all error fields are JSON serializable
    safe_details = []
    for err in errors:
        safe_err = {
            "loc": err.get("loc"),
            "msg": str(err.get("msg")),
            "type": err.get("type")
        }
        safe_details.append(safe_err)

    logger.warning(f"Validation Error [{code}] at {loc}: {msg}")
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": code,
                "message": f"Validation error at '{loc}': {msg}",
                "retryable": False,
                "details": safe_details
            }
        }
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(f"Unhandled Server Error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": ERR_INTERNAL_ERROR,
                "message": "An unexpected internal server error occurred.",
                "retryable": True,
                "details": str(exc)
            }
        }
    )

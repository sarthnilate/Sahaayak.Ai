import json
import logging
import re
import uuid
from typing import Any, Dict, Optional

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

# ==============================================================================
# Domain Exceptions
# ==============================================================================


class SahaayakException(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.code = code
        self.error_code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class EntityNotFoundError(SahaayakException):
    def __init__(
        self,
        entity_name: str = "Resource",
        entity_id: str = "",
        message: Optional[str] = None,
        error_code: Optional[str] = None,
        entity_type: Optional[str] = None,
    ):
        resolved_name = entity_type or entity_name
        code = error_code or f"{resolved_name.upper()}_NOT_FOUND"
        msg = message or f"{resolved_name} with identifier '{entity_id}' was not found."
        super().__init__(
            code=code,
            message=msg,
            status_code=404,
        )


class InvalidStateTransitionError(SahaayakException):
    def __init__(
        self,
        entity: str = "Resource",
        current_state: str = "",
        attempted_state: str = "",
        message: Optional[str] = None,
        error_code: Optional[str] = None,
    ):
        code = error_code or "INVALID_STATE_TRANSITION"
        msg = message or f"Cannot transition {entity} from '{current_state}' to '{attempted_state}'."
        super().__init__(
            code=code,
            message=msg,
            status_code=400,
            details={"current_state": current_state, "attempted_state": attempted_state},
        )


class PriorityOverrideMissingReasonError(SahaayakException):
    def __init__(self):
        super().__init__(
            code="PRIORITY_OVERRIDE_REASON_REQUIRED",
            message="Overriding the AI suggested priority requires a documented justification reason.",
            status_code=400,
        )


class AuditMutationForbiddenError(SahaayakException):
    def __init__(self, action: str):
        super().__init__(
            code="AUDIT_MUTATION_FORBIDDEN",
            message=f"Audit events are immutable by safety policy. Attempted operation '{action}' is strictly forbidden.",
            status_code=403,
        )


class AIProviderError(SahaayakException):
    def __init__(self, message: str, provider: str = "gemini"):
        super().__init__(
            code="AI_PROVIDER_ERROR",
            message=f"AI inference error from {provider}: {message}",
            status_code=502,
        )


class AiTimeoutError(SahaayakException):
    def __init__(self, message: str = "AI inference timed out after configured deadline", provider: str = "gemini"):
        super().__init__(
            code="AI_TIMEOUT",
            message=f"{provider.upper()} extraction timed out: {message}",
            status_code=504,
        )


class AiRateLimitError(SahaayakException):
    def __init__(self, message: str = "AI service rate limit exceeded", provider: str = "gemini"):
        super().__init__(
            code="AI_RATE_LIMIT",
            message=f"{provider.upper()} quota or rate limit exceeded: {message}",
            status_code=429,
        )


class AiMalformedOutputError(SahaayakException):
    def __init__(self, message: str = "AI returned response that violates required schema", provider: str = "gemini"):
        super().__init__(
            code="AI_MALFORMED_OUTPUT",
            message=f"{provider.upper()} output could not be validated against schema: {message}",
            status_code=502,
        )


class AiSafetyBlockError(SahaayakException):
    def __init__(self, message: str = "Content blocked by safety filters", provider: str = "gemini"):
        super().__init__(
            code="AI_SAFETY_BLOCK",
            message=f"{provider.upper()} safety filters blocked the input or response: {message}",
            status_code=422,
        )


class AiAuthenticationError(SahaayakException):
    def __init__(self, message: str = "Invalid or missing AI API credentials", provider: str = "gemini"):
        super().__init__(
            code="AI_AUTH_ERROR",
            message=f"{provider.upper()} authentication failed: {message}",
            status_code=502,
        )


class AuthenticationRequiredError(SahaayakException):
    def __init__(
        self,
        message: str = "Authentication credentials required",
        error_code: str = "UNAUTHENTICATED",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(code=error_code, message=message, status_code=401, details=details)


class ForbiddenError(SahaayakException):
    def __init__(
        self,
        message: str = "Operation not permitted",
        error_code: str = "PERMISSION_DENIED",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(code=error_code, message=message, status_code=403, details=details)


class BadRequestError(SahaayakException):
    def __init__(
        self,
        message: str,
        error_code: str = "BAD_REQUEST",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(code=error_code, message=message, status_code=400, details=details)


class ResourceNotFoundError(SahaayakException):
    def __init__(
        self,
        message: str = "Resource not found",
        error_code: str = "RESOURCE_NOT_FOUND",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(code=error_code, message=message, status_code=404, details=details)


class ConflictError(SahaayakException):
    def __init__(
        self,
        message: str,
        error_code: str = "RESOURCE_ALREADY_EXISTS",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(code=error_code, message=message, status_code=409, details=details)


# ==============================================================================
# Structured Logging with Redaction Filter
# ==============================================================================

SENSITIVE_PATTERNS = [
    (
        re.compile(
            r'("?(?:password|token|secret|jwt|api_key|gemini_api_key)"?\s*[:=]\s*)"([^"]+)"',
            re.IGNORECASE,
        ),
        r'\1"***REDACTED***"',
    ),
    (
        re.compile(r'("?(?:original_text|body|report_body)"?\s*[:=]\s*)"([^"]+)"', re.IGNORECASE),
        r'\1"[REDACTED_REPORT_CONTENT]"',
    ),
    (re.compile(r"(Bearer\s+)[A-Za-z0-9_\-\.]+", re.IGNORECASE), r"\1***REDACTED_TOKEN***"),
    (re.compile(r"(AIza[0-9A-Za-z-_]{35})"), r"***REDACTED_GEMINI_KEY***"),
]


class RedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for pattern, repl in SENSITIVE_PATTERNS:
                record.msg = pattern.sub(repl, record.msg)
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id
        return json.dumps(log_obj)


logger = logging.getLogger("sahaayak")
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
handler.addFilter(RedactionFilter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# ==============================================================================
# Request ID Middleware
# ==============================================================================


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Honor client request-id if provided, otherwise generate a secure UUID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# ==============================================================================
# Standard Error Envelope Helpers & Exception Handlers
# ==============================================================================


def make_error_envelope(
    code: str, message: str, request_id: str, details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    return {
        "error_code": code,
        "detail": message,
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
            "request_id": request_id,
        },
    }


async def sahaayak_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    domain_exc = (
        exc if isinstance(exc, SahaayakException) else SahaayakException("DOMAIN_ERROR", str(exc))
    )
    request_id = getattr(request.state, "request_id", "unknown")
    logger.warning(
        f"Domain exception: code={domain_exc.code} message={domain_exc.message}",
        extra={"request_id": request_id},
    )
    return JSONResponse(
        status_code=domain_exc.status_code,
        content=make_error_envelope(
            code=domain_exc.code,
            message=domain_exc.message,
            request_id=request_id,
            details=domain_exc.details,
        ),
    )


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    status_code = getattr(exc, "status_code", 400)
    detail = getattr(exc, "detail", str(exc))
    code = "RESOURCE_NOT_FOUND" if status_code == 404 else f"HTTP_{status_code}"
    return JSONResponse(
        status_code=status_code,
        content=make_error_envelope(code=code, message=str(detail), request_id=request_id),
    )


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    errors_data: Any = getattr(exc, "errors", lambda: [])()
    return JSONResponse(
        status_code=422,
        content=make_error_envelope(
            code="REQUEST_VALIDATION_ERROR",
            message="Request parameter or body failed schema validation.",
            request_id=request_id,
            details={"errors": str(errors_data)},
        ),
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    # Log internal error safely without exposing stack trace to the client
    logger.error(
        f"Unhandled server error: {type(exc).__name__}: {str(exc)}",
        extra={"request_id": request_id},
    )
    return JSONResponse(
        status_code=500,
        content=make_error_envelope(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected internal server error occurred. Please reference the request ID.",
            request_id=request_id,
        ),
    )

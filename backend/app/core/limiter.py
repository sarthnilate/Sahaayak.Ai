from backend.app.core.auth import AUTH_COOKIE_NAME, decode_access_token
from backend.app.core.config import settings
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def get_rate_limit_key(request: Request) -> str:
    """
    Returns rate limit key: authenticated user ID if logged in, otherwise remote client IP.
    """
    token = request.cookies.get(AUTH_COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]

    if token:
        try:
            payload = decode_access_token(token)
            user_id = payload.get("sub")
            if user_id:
                return f"user:{user_id}"
        except Exception:
            pass

    return f"ip:{get_remote_address(request)}"


limiter = Limiter(
    key_func=get_rate_limit_key, default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"]
)

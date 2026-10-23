import secrets
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError
from backend.app.core.config import settings
from backend.app.core.errors import AuthenticationRequiredError, BadRequestError, ForbiddenError
from backend.app.db.session import get_db
from backend.app.models.all_models import RoleEnum, User
from fastapi import Cookie, Depends, Header, Request, Response
from sqlalchemy.orm import Session

# Argon2 Password Hasher
pwd_hasher = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=1)

# Cookie & Token Constants
AUTH_COOKIE_NAME = "access_token"
CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Common breached passwords list
COMMON_BREACHED_PASSWORDS = {
    "password",
    "password123",
    "admin123",
    "12345678",
    "qwerty123",
    "welcome123",
    "letmein123",
    "coordinator123",
    "sahaayak123",
    "changeme",
}


def hash_password(plain_password: str) -> str:
    return pwd_hasher.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, Exception):
        return False


def validate_password_strength(password: str) -> None:
    if len(password) < 8:
        raise BadRequestError(
            message="Password must be at least 8 characters long", error_code="WEAK_PASSWORD"
        )
    if password.lower() in COMMON_BREACHED_PASSWORDS:
        raise BadRequestError(
            message="Password contains a commonly breached or insecure pattern",
            error_code="BREACHED_PASSWORD",
        )


def create_access_token(user_id: str, role: str, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=JWT_EXPIRE_MINUTES))
    payload = {"sub": user_id, "role": role, "exp": expire, "iat": datetime.now(timezone.utc)}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationRequiredError(
            message="Authentication session expired. Please log in again.",
            error_code="SESSION_EXPIRED",
        )
    except (jwt.InvalidTokenError, Exception):
        raise AuthenticationRequiredError(
            message="Invalid authentication credentials.", error_code="INVALID_TOKEN"
        )


def generate_csrf_token() -> str:
    return secrets.token_hex(32)


def set_auth_cookies(response: Response, token: str, csrf_token: str) -> None:
    is_prod = settings.ENVIRONMENT.lower() == "production"
    # HTTP-only authentication cookie
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=is_prod,
        max_age=JWT_EXPIRE_MINUTES * 60,
        path="/",
    )
    # Readable CSRF cookie for client double-submit pattern
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        samesite="lax",
        secure=is_prod,
        max_age=JWT_EXPIRE_MINUTES * 60,
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(key=AUTH_COOKIE_NAME, path="/")
    response.delete_cookie(key=CSRF_COOKIE_NAME, path="/")


def verify_csrf_header(
    request: Request,
    csrf_cookie: Optional[str] = Cookie(None, alias=CSRF_COOKIE_NAME),
    csrf_header: Optional[str] = Header(None, alias="X-CSRF-Token"),
) -> None:
    """
    Enforces double-submit CSRF protection on state-changing requests.
    """
    # Allow safe read-only methods without CSRF
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return

    # Skip login and registration initial token setup
    path = request.url.path
    if path.endswith("/auth/login") or path.endswith("/auth/register"):
        return

    if not csrf_cookie or not csrf_header or not secrets.compare_digest(csrf_cookie, csrf_header):
        raise ForbiddenError(
            message="CSRF validation failed: Missing or mismatched X-CSRF-Token header",
            error_code="CSRF_VALIDATION_FAILED",
        )


def get_current_user_optional(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """
    Retrieves currently authenticated user from cookie or Authorization Bearer header,
    returning None if unauthenticated.
    """
    token = request.cookies.get(AUTH_COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]

    if not token:
        return None

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            return None
        return db.get(User, user_id)
    except Exception:
        return None


def get_current_user(user: Optional[User] = Depends(get_current_user_optional)) -> User:
    """
    Strict dependency: enforces user is authenticated.
    """
    if not user:
        raise AuthenticationRequiredError(
            message="Authentication required to access this resource", error_code="UNAUTHENTICATED"
        )
    return user


def require_role(*allowed_roles: RoleEnum) -> Callable[[User], User]:
    """
    Reusable RBAC role requirement dependency factory.
    Example: Depends(require_role(RoleEnum.COORDINATOR, RoleEnum.ADMIN))
    """

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise ForbiddenError(
                message=f"Access denied: user role '{current_user.role.value}' does not have permission",
                error_code="INSUFFICIENT_PERMISSIONS",
            )
        return current_user

    return dependency

from datetime import datetime, timedelta, timezone

from backend.app.core.auth import (
    clear_auth_cookies,
    create_access_token,
    generate_csrf_token,
    get_current_user,
    hash_password,
    set_auth_cookies,
    validate_password_strength,
    verify_password,
)
from backend.app.core.errors import (
    AuthenticationRequiredError,
    ConflictError,
)
from backend.app.db.session import get_db
from backend.app.models.all_models import RoleEnum, User
from backend.app.schemas.all_schemas import (
    AuthResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

router = APIRouter(prefix="/auth", tags=["Authentication & RBAC"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegisterRequest, response: Response, db: Session = Depends(get_db)):
    """
    Registers a new user.
    CRITICAL SECURITY RULE: Role is strictly locked to 'reporter' ONLY.
    Any attempt to request coordinator or admin role is ignored.
    """
    email_clean = payload.email.strip().lower()
    username_clean = payload.username.strip().lower()

    # 1. Validate password policy
    validate_password_strength(payload.password)

    # 2. Check for duplicate email or username
    existing_user = db.execute(
        select(User).where(or_(User.email == email_clean, User.username == username_clean))
    ).scalar_one_or_none()

    if existing_user:
        raise ConflictError(
            message="An account with this email or username already exists",
            error_code="USER_ALREADY_EXISTS",
        )

    # 3. Create user with role strictly enforced as REPORTER
    hashed_pwd = hash_password(payload.password)
    user = User(
        email=email_clean,
        username=username_clean,
        hashed_password=hashed_pwd,
        role=RoleEnum.REPORTER,  # STRICT ENFORCEMENT: ignore any role field
        full_name=payload.full_name.strip() if payload.full_name else None,
        failed_login_attempts=0,
        locked_until=None,
    )
    db.add(user)
    db.flush()

    # 4. Audit trail
    from backend.app.services.audit.service import AuditService

    AuditService.record(
        db=db,
        actor=user.email,
        action="USER_REGISTERED",
        entity_type="user",
        entity_id=user.id,
        before={},
        after={"email": user.email, "username": user.username, "role": user.role.value},
    )
    db.refresh(user)

    # 5. Issue JWT and CSRF double-submit token
    token = create_access_token(user.id, user.role.value)
    csrf_token = generate_csrf_token()
    set_auth_cookies(response, token, csrf_token)

    return AuthResponse(
        user=UserResponse.model_validate(user),
        message="Registration successful. Welcome to Sahaayak AI.",
        csrf_token=csrf_token,
    )


@router.post("/login", response_model=AuthResponse, status_code=status.HTTP_200_OK)
def login(payload: UserLoginRequest, response: Response, db: Session = Depends(get_db)):
    """
    Authenticates user with login lockout throttling and generic error messages
    to prevent username/email enumeration.
    """
    identifier = payload.email.strip().lower()
    now = datetime.now(timezone.utc)

    # Lookup by email or username
    user = db.execute(
        select(User).where(or_(User.email == identifier, User.username == identifier))
    ).scalar_one_or_none()

    # Generic credential rejection to prevent user enumeration
    generic_error = AuthenticationRequiredError(
        message="Invalid email or password", error_code="INVALID_CREDENTIALS"
    )

    if not user:
        raise generic_error

    # Check lockout
    if user.locked_until:
        locked_until_utc = user.locked_until
        if locked_until_utc.tzinfo is None:
            locked_until_utc = locked_until_utc.replace(tzinfo=timezone.utc)
        if locked_until_utc > now:
            raise AuthenticationRequiredError(
                message="Account is temporarily locked due to multiple failed login attempts. Please try again later.",
                error_code="ACCOUNT_LOCKED",
            )

    # Verify password
    if not verify_password(payload.password, user.hashed_password):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= 5:
            user.locked_until = now + timedelta(minutes=15)
        db.commit()
        raise generic_error

    # Reset lockout on successful login
    user.failed_login_attempts = 0
    user.locked_until = None

    # Audit login
    from backend.app.services.audit.service import AuditService

    AuditService.record(
        db=db,
        actor=user.email,
        action="USER_LOGIN",
        entity_type="user",
        entity_id=user.id,
        before={},
        after={"role": user.role.value},
    )

    # Generate JWT and CSRF tokens
    token = create_access_token(user.id, user.role.value)
    csrf_token = generate_csrf_token()
    set_auth_cookies(response, token, csrf_token)

    return AuthResponse(
        user=UserResponse.model_validate(user),
        message="Authentication successful",
        csrf_token=csrf_token,
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(response: Response):
    """
    Clears HTTP-only JWT and CSRF cookies.
    """
    clear_auth_cookies(response)
    return {"status": "success", "message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Returns currently authenticated user profile.
    """
    return UserResponse.model_validate(current_user)

from typing import Annotated

import structlog
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from psx_api.config import settings
from psx_api.database import get_db
from psx_api.redis_client import get_redis
from psx_api.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    ResetPasswordRequest,
    SignupRequest,
    TotpSetupResponse,
    TotpVerifyRequest,
    UserResponse,
    UserSettingsUpdate,
    VerifyEmailRequest,
)
from psx_api.services.auth_service import AuthError, AuthService
from psx_api.services.rate_limiter import LoginRateLimiter

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_COOKIE_NAME = "psx_session"
_COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days in seconds

DbDep = Annotated[AsyncSession, Depends(get_db)]
RedisDep = Annotated[Redis, Depends(get_redis)]  # type: ignore[type-arg]


def _service(db: DbDep, redis: RedisDep) -> AuthService:
    return AuthService(db, redis)


ServiceDep = Annotated[AuthService, Depends(_service)]


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=_COOKIE_NAME,
        value=token,
        max_age=_COOKIE_MAX_AGE,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=_COOKIE_NAME, path="/")


async def _get_current_user(
    service: ServiceDep,
    psx_session: Annotated[str | None, Cookie()] = None,
) -> "from psx_api.models.users import User":  # type: ignore[return]
    from psx_api.models.users import User as UserModel
    if not psx_session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    user = await service.get_session_user(psx_session)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
    return user


CurrentUser = Annotated[object, Depends(_get_current_user)]


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(body: SignupRequest, service: ServiceDep) -> dict[str, str]:
    try:
        user = await service.signup(body.email, body.password, body.full_name)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    return {"message": "Account created. Please check your email to verify your address.", "user_id": user.id}


@router.post("/verify-email")
async def verify_email(body: VerifyEmailRequest, service: ServiceDep) -> dict[str, str]:
    try:
        await service.verify_email(body.token)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    return {"message": "Email verified successfully."}


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    service: ServiceDep,
    redis: RedisDep,
) -> LoginResponse:
    ip = request.client.host if request.client else "unknown"
    limiter = LoginRateLimiter(redis)

    if await limiter.is_blocked(ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Try again in 1 hour.",
        )

    user_agent = request.headers.get("user-agent")

    try:
        user, token = await service.login(
            body.email, body.password, body.totp_code, user_agent, ip
        )
    except AuthError as exc:
        await limiter.record_failure(ip)
        raise HTTPException(status_code=exc.status_code, detail=str(exc))

    await limiter.clear(ip)
    _set_session_cookie(response, token)

    return LoginResponse(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        email_verified=user.email_verified_at is not None,
        totp_enabled=user.totp_enabled,
        shariah_mode=user.shariah_mode,
    )


@router.post("/logout")
async def logout(
    response: Response,
    service: ServiceDep,
    psx_session: Annotated[str | None, Cookie()] = None,
) -> dict[str, str]:
    if psx_session:
        await service.logout(psx_session)
    _clear_session_cookie(response)
    return {"message": "Logged out."}


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUser) -> UserResponse:
    return UserResponse.from_user(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_me(
    body: UserSettingsUpdate,
    current_user: CurrentUser,
    db: DbDep,
) -> UserResponse:
    from psx_api.models.users import User
    user: User = current_user  # type: ignore[assignment]
    if body.shariah_mode is not None:
        user.shariah_mode = body.shariah_mode
    if body.is_filer is not None:
        user.is_filer = body.is_filer
    if body.full_name is not None:
        user.full_name = body.full_name
    if body.share_anonymously is not None:
        user.share_anonymously = body.share_anonymously
    if body.date_of_birth is not None:
        from datetime import date as _date
        try:
            user.date_of_birth = _date.fromisoformat(body.date_of_birth)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="date_of_birth must be YYYY-MM-DD.",
            )
    await db.flush()
    return UserResponse.from_user(user)


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest, service: ServiceDep) -> dict[str, str]:
    await service.forgot_password(body.email)
    return {"message": "If that email exists, a reset link has been sent."}


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest, service: ServiceDep) -> dict[str, str]:
    try:
        await service.reset_password(body.token, body.new_password)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    return {"message": "Password reset successfully. Please log in."}


@router.post("/totp/setup", response_model=TotpSetupResponse)
async def totp_setup(current_user: CurrentUser, service: ServiceDep) -> TotpSetupResponse:
    from psx_api.models.users import User as UserModel
    result = await service.totp_setup(current_user)  # type: ignore[arg-type]
    return TotpSetupResponse(**result)


@router.post("/totp/confirm")
async def totp_confirm(
    body: TotpVerifyRequest,
    current_user: CurrentUser,
    service: ServiceDep,
) -> dict[str, str]:
    try:
        await service.totp_confirm(current_user, body.totp_code)  # type: ignore[arg-type]
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    return {"message": "Two-factor authentication enabled."}


@router.post("/totp/disable")
async def totp_disable(
    body: TotpVerifyRequest,
    current_user: CurrentUser,
    service: ServiceDep,
) -> dict[str, str]:
    try:
        await service.totp_disable(current_user, body.totp_code)  # type: ignore[arg-type]
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    return {"message": "Two-factor authentication disabled."}

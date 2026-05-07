from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str | None = Field(None, min_length=1, max_length=255)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: str | None = Field(None, pattern=r"^\d{6}$")


class LoginResponse(BaseModel):
    message: str = "Login successful"
    user_id: str
    email: str
    full_name: str | None
    email_verified: bool
    totp_enabled: bool
    shariah_mode: bool


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter")
        return v


class VerifyEmailRequest(BaseModel):
    token: str


class TotpSetupResponse(BaseModel):
    secret: str
    provisioning_uri: str


class TotpVerifyRequest(BaseModel):
    totp_code: str = Field(..., pattern=r"^\d{6}$")


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: str | None
    email_verified: bool
    is_filer: bool
    shariah_mode: bool
    totp_enabled: bool
    created_at: datetime

    @classmethod
    def from_user(cls, user: object) -> "UserResponse":
        from psx_api.models.users import User
        u: User = user  # type: ignore[assignment]
        return cls(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            email_verified=u.email_verified_at is not None,
            is_filer=u.is_filer,
            shariah_mode=u.shariah_mode,
            totp_enabled=u.totp_enabled,
            created_at=u.created_at,
        )

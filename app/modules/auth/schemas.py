import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator


class SendOTPRequest(BaseModel):
    phone_number: str = Field(
        ..., 
        description="User phone number in E.164 format (e.g. +919876543210)"
    )

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        # Strip spaces/dashes
        cleaned = v.replace(" ", "").replace("-", "")
        # Basic validation: starts with + or contains digits
        if not (cleaned.startswith("+") and cleaned[1:].isdigit()) and not cleaned.isdigit():
            raise ValueError("Phone number must contain only digits and start with + if E.164.")
        if len(cleaned) < 10 or len(cleaned) > 15:
            raise ValueError("Phone number must be between 10 and 15 characters long.")
        return cleaned


class SendOTPResponse(BaseModel):
    success: bool
    request_id: str
    message: str = "OTP sent successfully."


class VerifyOTPRequest(BaseModel):
    phone_number: str = Field(...)
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit numeric OTP code")
    request_id: str = Field(..., description="Unique request ID returned from send-otp")

    @field_validator("otp")
    @classmethod
    def validate_numeric_otp(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("OTP must contain only numbers.")
        return v


class UserResponse(BaseModel):
    id: uuid.UUID
    phone_number: str
    email: str | None
    role: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class VerifyOTPResponse(BaseModel):
    success: bool
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

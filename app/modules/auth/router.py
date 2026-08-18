from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.security import create_access_token
from app.modules.auth.schemas import (
    SendOTPRequest, 
    SendOTPResponse, 
    VerifyOTPRequest, 
    VerifyOTPResponse,
    UserResponse
)
from app.modules.auth.rate_limit import check_otp_send_rate_limit, check_otp_verify_rate_limit
from app.modules.auth.service import send_otp, verify_otp

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/send-otp", response_model=SendOTPResponse)
async def api_send_otp(
    request: Request,
    payload: SendOTPRequest,
    db: AsyncSession = Depends(get_db)
):
    """Trigger a verification OTP text message to the specified phone number."""
    client_ip = request.client.host if request.client else "unknown"
    
    # 1. Enforce Redis Rate Limiting (IP & phone-level check)
    await check_otp_send_rate_limit(payload.phone_number, client_ip)
    
    # 2. Invoke Auth service logic
    request_id = await send_otp(db, payload.phone_number)
    
    return SendOTPResponse(
        success=True,
        request_id=request_id,
        message="Verification OTP code successfully sent to your phone."
    )


@router.post("/verify-otp", response_model=VerifyOTPResponse)
async def api_verify_otp(
    request: Request,
    payload: VerifyOTPRequest,
    db: AsyncSession = Depends(get_db)
):
    """Verify OTP code against stored request ID and issue session JWT tokens."""
    client_ip = request.client.host if request.client else "unknown"
    
    # 1. Enforce Redis Rate Limiting (IP & phone-level check)
    await check_otp_verify_rate_limit(payload.phone_number, client_ip)
    
    # 2. Verify OTP in DB & fetch/register User
    user = await verify_otp(
        db, 
        payload.phone_number, 
        payload.otp, 
        payload.request_id
    )
    
    # 3. Create Session Token
    access_token = create_access_token(subject=user.id, role=user.role)
    
    return VerifyOTPResponse(
        success=True,
        access_token=access_token,
        user=UserResponse.model_validate(user)
    )

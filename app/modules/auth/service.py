from datetime import datetime, timedelta, timezone
import hashlib
import secrets
import uuid
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppException
from app.infrastructure.aws.sns.provider import get_sms_provider
from app.modules.auth.models import OTPState
from app.modules.users.models import User

logger = structlog.get_logger()


def _generate_otp_code() -> str:
    """Generate a secure 6-digit numeric OTP code."""
    # Using secrets.choice for cryptographic randomness
    return "".join(secrets.choice("0123456789") for _ in range(6))


def _hash_otp_code(otp: str) -> str:
    """Securely hash the OTP code using SHA-256."""
    return hashlib.sha256(otp.encode("utf-8")).hexdigest()


async def send_otp(db: AsyncSession, phone_number: str) -> str:
    """Generate, save, and transmit an OTP code to a phone number.
    
    Returns:
        The generated unique request_id.
    """
    raw_otp = _generate_otp_code()
    hashed_otp = _hash_otp_code(raw_otp)
    
    request_id = uuid.uuid4().hex
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.OTP_EXPIRATION_SECONDS)
    
    # Store OTP state in database
    otp_state = OTPState(
        phone_number=phone_number,
        hashed_otp=hashed_otp,
        expires_at=expires_at,
        request_id=request_id,
        status="PENDING",
        attempt_count=0,
        max_attempts=settings.OTP_MAX_ATTEMPTS
    )
    db.add(otp_state)
    await db.commit()
    
    # Send OTP SMS using abstract SMSProvider
    sms_provider = get_sms_provider()
    sms_text = f"Your StudioLive verification OTP is: {raw_otp}. Valid for 5 minutes."
    
    # Send SMS (Mock provider will just print to console/logs)
    sms_sent = await sms_provider.send_sms(phone_number, sms_text)
    
    if not sms_sent:
        logger.error("otp_sms_delivery_failed", phone_number=phone_number, request_id=request_id)
        # We don't rollback DB state since the OTP was successfully saved, 
        # but we notify the client that SMS delivery failed.
        raise AppException(
            code="SMS_DELIVERY_FAILED",
            message="Failed to transmit OTP SMS. Please try again.",
            status_code=500
        )
        
    return request_id


async def verify_otp(db: AsyncSession, phone_number: str, otp: str, request_id: str) -> User:
    """Verify an OTP code, register new users, and return the User instance."""
    # Fetch active OTP state
    result = await db.execute(
        select(OTPState).filter_by(request_id=request_id, phone_number=phone_number)
    )
    otp_state = result.scalar_one_or_none()
    
    if not otp_state:
        raise AppException(
            code="OTP_INVALID",
            message="Invalid verification request ID or phone number.",
            status_code=400
        )
        
    # Check if OTP is already consumed/failed
    if otp_state.status != "PENDING":
        raise AppException(
            code="OTP_CONSUMED",
            message="This OTP has already been verified or invalidated.",
            status_code=400
        )
        
    # Check expiration
    if datetime.now(timezone.utc) > otp_state.expires_at:
        otp_state.status = "EXPIRED"
        await db.commit()
        raise AppException(
            code="OTP_EXPIRED",
            message="This OTP has expired. Please request a new one.",
            status_code=400
        )
        
    # Check attempt limits
    if otp_state.attempt_count >= otp_state.max_attempts:
        otp_state.status = "FAILED"
        await db.commit()
        raise AppException(
            code="OTP_ATTEMPTS_EXCEEDED",
            message="Too many failed verification attempts. This OTP is now invalid.",
            status_code=400
        )
        
    # Secure comparison to avoid timing attacks
    input_hashed = _hash_otp_code(otp)
    if not secrets.compare_digest(otp_state.hashed_otp, input_hashed):
        # Increment attempt count
        otp_state.attempt_count += 1
        if otp_state.attempt_count >= otp_state.max_attempts:
            otp_state.status = "FAILED"
            await db.commit()
            raise AppException(
                code="OTP_ATTEMPTS_EXCEEDED",
                message="Too many failed verification attempts. This OTP is now invalid.",
                status_code=400
            )
            
        await db.commit()
        raise AppException(
            code="OTP_INVALID",
            message="Incorrect OTP code. Please try again.",
            status_code=400
        )
        
    # OTP is valid, mark as verified
    otp_state.status = "VERIFIED"
    otp_state.verified_at = datetime.now(timezone.utc)
    
    # Retrieve or create user record
    result_user = await db.execute(
        select(User).filter_by(phone_number=phone_number)
    )
    user = result_user.scalar_one_or_none()
    
    if not user:
        # Register new customer
        user = User(
            phone_number=phone_number,
            role="CUSTOMER",
            is_active=True
        )
        db.add(user)
        logger.info("new_user_registered", phone_number=phone_number)
        
    elif not user.is_active:
        await db.commit()
        raise AppException(
            code="USER_DEACTIVATED",
            message="This account has been deactivated.",
            status_code=403
        )
        
    await db.commit()
    await db.refresh(user)
    return user

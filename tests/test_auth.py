from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import OTPState
from app.modules.users.models import User


@pytest.mark.asyncio
async def test_send_otp_success(client: AsyncClient, db_session: AsyncSession):
    """Test successful OTP request generates database record and SMS dispatch."""
    with patch("app.modules.auth.service._generate_otp_code", return_value="888888"):
        response = await client.post(
            "/api/v1/auth/send-otp",
            json={"phone_number": "+919876543210"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "request_id" in data
        
        # Verify OTPState record created in PostgreSQL
        result = await db_session.execute(
            select(OTPState).filter_by(request_id=data["request_id"])
        )
        otp_state = result.scalar_one_or_none()
        
        assert otp_state is not None
        assert otp_state.phone_number == "+919876543210"
        assert otp_state.status == "PENDING"
        assert otp_state.attempt_count == 0


@pytest.mark.asyncio
async def test_send_otp_validation_errors(client: AsyncClient):
    """Test validation errors for malformed phone formats."""
    # Invalid length (too short)
    response = await client.post(
        "/api/v1/auth/send-otp",
        json={"phone_number": "123"}
    )
    assert response.status_code == 422
    
    # Non-numeric format
    response = await client.post(
        "/api/v1/auth/send-otp",
        json={"phone_number": "+abc12345678"}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_verify_otp_success_new_user_registration(client: AsyncClient, db_session: AsyncSession):
    """Test verifying correct OTP creates user profile and generates session JWT."""
    with patch("app.modules.auth.service._generate_otp_code", return_value="123456"):
        # 1. Request OTP
        send_response = await client.post(
            "/api/v1/auth/send-otp",
            json={"phone_number": "+917777777777"}
        )
        request_id = send_response.json()["request_id"]
        
        # 2. Verify Correct OTP
        verify_response = await client.post(
            "/api/v1/auth/verify-otp",
            json={
                "phone_number": "+917777777777",
                "otp": "123456",
                "request_id": request_id
            }
        )
        
        assert verify_response.status_code == 200
        data = verify_response.json()
        assert data["success"] is True
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["phone_number"] == "+917777777777"
        assert data["user"]["role"] == "CUSTOMER"
        assert data["user"]["is_active"] is True
        
        # Verify user was saved in database
        result_user = await db_session.execute(
            select(User).filter_by(phone_number="+917777777777")
        )
        user = result_user.scalar_one_or_none()
        assert user is not None
        assert user.role == "CUSTOMER"
        
        # Verify OTP status updated to VERIFIED in DB
        result_otp = await db_session.execute(
            select(OTPState).filter_by(request_id=request_id)
        )
        otp_state = result_otp.scalar_one_or_none()
        assert otp_state.status == "VERIFIED"
        assert otp_state.verified_at is not None


@pytest.mark.asyncio
async def test_verify_otp_invalid_code(client: AsyncClient, db_session: AsyncSession):
    """Test entering incorrect code increments attempt counter."""
    with patch("app.modules.auth.service._generate_otp_code", return_value="123456"):
        # 1. Request OTP
        send_response = await client.post(
            "/api/v1/auth/send-otp",
            json={"phone_number": "+918888888888"}
        )
        request_id = send_response.json()["request_id"]
        
        # 2. Verify with Incorrect Code
        verify_response = await client.post(
            "/api/v1/auth/verify-otp",
            json={
                "phone_number": "+918888888888",
                "otp": "999999",  # incorrect code
                "request_id": request_id
            }
        )
        
        assert verify_response.status_code == 400
        data = verify_response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "OTP_INVALID"
        
        # Verify attempt_count was incremented in database
        result_otp = await db_session.execute(
            select(OTPState).filter_by(request_id=request_id)
        )
        otp_state = result_otp.scalar_one_or_none()
        assert otp_state.attempt_count == 1
        assert otp_state.status == "PENDING"


@pytest.mark.asyncio
async def test_verify_otp_brute_force_protection(client: AsyncClient, db_session: AsyncSession):
    """Test OTP code is invalidated after reaching 5 failed attempts."""
    with patch("app.modules.auth.service._generate_otp_code", return_value="123456"):
        # 1. Request OTP
        send_response = await client.post(
            "/api/v1/auth/send-otp",
            json={"phone_number": "+919999999999"}
        )
        request_id = send_response.json()["request_id"]
        
        # 2. Force 5 consecutive invalid attempts
        for i in range(5):
            response = await client.post(
                "/api/v1/auth/verify-otp",
                json={
                    "phone_number": "+919999999999",
                    "otp": "000000",
                    "request_id": request_id
                }
            )
            assert response.status_code == 400
            
        # Verify OTPState status is now FAILED in DB
        result_otp = await db_session.execute(
            select(OTPState).filter_by(request_id=request_id)
        )
        otp_state = result_otp.scalar_one_or_none()
        assert otp_state.status == "FAILED"
        
        # 3. 6th attempt with CORRECT code should be blocked by Redis rate limiting
        verify_response = await client.post(
            "/api/v1/auth/verify-otp",
            json={
                "phone_number": "+919999999999",
                "otp": "123456",
                "request_id": request_id
            }
        )
        assert verify_response.status_code == 429
        assert verify_response.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"


@pytest.mark.asyncio
async def test_verify_otp_expired(client: AsyncClient, db_session: AsyncSession):
    """Test verification fail if the OTP expiration limit has passed."""
    with patch("app.modules.auth.service._generate_otp_code", return_value="123456"):
        # 1. Request OTP
        send_response = await client.post(
            "/api/v1/auth/send-otp",
            json={"phone_number": "+916666666666"}
        )
        request_id = send_response.json()["request_id"]
        
        # Update expires_at to the past in database
        result_otp = await db_session.execute(
            select(OTPState).filter_by(request_id=request_id)
        )
        otp_state = result_otp.scalar_one_or_none()
        otp_state.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        await db_session.commit()
        
        # 2. Try to verify expired OTP
        verify_response = await client.post(
            "/api/v1/auth/verify-otp",
            json={
                "phone_number": "+916666666666",
                "otp": "123456",
                "request_id": request_id
            }
        )
        assert verify_response.status_code == 400
        assert verify_response.json()["error"]["code"] == "OTP_EXPIRED"

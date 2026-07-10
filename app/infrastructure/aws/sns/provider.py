import abc
import asyncio
from typing import Any
import boto3
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class SMSProvider(abc.ABC):
    """Abstract Base Class for SMS communication."""
    
    @abc.abstractmethod
    async def send_sms(self, phone_number: str, message: str) -> bool:
        """Send an SMS to a phone number.
        
        Args:
            phone_number: Destination phone number in E.164 format.
            message: Plain text body of the SMS.
            
        Returns:
            True if sending succeeded, False otherwise.
        """
        pass


class MockSMSProvider(SMSProvider):
    """Local SMS Provider that logs messages to console instead of invoking actual APIs."""
    
    async def send_sms(self, phone_number: str, message: str) -> bool:
        logger.info(
            "mock_sms_sent", 
            phone_number=phone_number, 
            message=message
        )
        return True


class AWSSNSProvider(SMSProvider):
    """AWS Simple Notification Service (SNS) provider for sending OTP SMS messages."""
    
    def __init__(self) -> None:
        kwargs: dict[str, Any] = {"region_name": settings.AWS_REGION}
        
        # Enable explicit credentials overrides for local integration testing if configured
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
            kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
            
        self.client = boto3.client("sns", **kwargs)

    async def send_sms(self, phone_number: str, message: str) -> bool:
        try:
            loop = asyncio.get_running_loop()
            
            # Execute the synchronous boto3 network call in the default executor thread pool
            # to avoid blocking FastAPI's async event loop.
            response = await loop.run_in_executor(
                None,
                lambda: self.client.publish(
                    PhoneNumber=phone_number,
                    Message=message,
                    MessageAttributes={
                        "AWS.SNS.SMS.SMSType": {
                            "DataType": "String",
                            "StringValue": "Transactional"
                        }
                    }
                )
            )
            
            message_id = response.get("MessageId")
            logger.info(
                "aws_sns_sms_sent", 
                phone_number=phone_number, 
                message_id=message_id
            )
            return True
            
        except Exception as e:
            logger.exception(
                "aws_sns_sms_failed", 
                phone_number=phone_number, 
                error=str(e)
            )
            return False


def get_sms_provider() -> SMSProvider:
    """Factory dependency to resolve configured SMS provider."""
    if settings.AWS_SNS_ENABLED:
        return AWSSNSProvider()
    return MockSMSProvider()

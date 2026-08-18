import redis.asyncio as aioredis
import structlog

from app.core.config import settings
from app.core.exceptions import RateLimitException

logger = structlog.get_logger()

# Connect to local/production Redis using settings connection URL
redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)


async def check_otp_send_rate_limit(phone_number: str, ip_address: str) -> None:
    """Enforce request limits for sending OTP SMS.
    
    Rules:
      - Max 1 request per 60 seconds per phone number (cooldown).
      - Max 5 requests per hour per phone number.
      - Max 10 requests per hour per IP address.
    """
    try:
        phone_sec_key = f"otp_send_limit:phone:sec:{phone_number}"
        phone_hour_key = f"otp_send_limit:phone:hour:{phone_number}"
        ip_hour_key = f"otp_send_limit:ip:hour:{ip_address}"
        
        # 1. Check 60s cooldown limit
        if await redis_client.get(phone_sec_key):
            raise RateLimitException("Please wait 60 seconds before requesting another OTP.")
            
        # 2. Check hourly phone limit
        phone_hourly = await redis_client.get(phone_hour_key)
        if phone_hourly and int(phone_hourly) >= 5:
            raise RateLimitException("Maximum OTP requests per hour exceeded for this phone number.")
            
        # 3. Check hourly IP limit
        ip_hourly = await redis_client.get(ip_hour_key)
        if ip_hourly and int(ip_hourly) >= 10:
            raise RateLimitException("Maximum OTP requests per hour exceeded for this IP address.")
            
        # Write limits atomically using pipelines
        async with redis_client.pipeline() as pipe:
            await pipe.set(phone_sec_key, "1", ex=60)
            
            if not phone_hourly:
                await pipe.set(phone_hour_key, "1", ex=3600)
            else:
                await pipe.incr(phone_hour_key)
                
            if not ip_hourly:
                await pipe.set(ip_hour_key, "1", ex=3600)
            else:
                await pipe.incr(ip_hour_key)
                
            await pipe.execute()
            
    except RateLimitException:
        raise
    except Exception as e:
        # Fail-open if Redis is offline: logs warn, but continues.
        # DB attempt-verification count provides safety for brute forcing.
        logger.error("redis_rate_limiter_offline", error=str(e))


async def check_otp_verify_rate_limit(phone_number: str, ip_address: str) -> None:
    """Enforce limits for verification attempts.
    
    Rules:
      - Max 5 verification attempts per 10 minutes per phone number.
      - Max 10 verification attempts per 10 minutes per IP.
    """
    try:
        phone_key = f"otp_verify_limit:phone:{phone_number}"
        ip_key = f"otp_verify_limit:ip:{ip_address}"
        
        # Check limits
        phone_count = await redis_client.get(phone_key)
        if phone_count and int(phone_count) >= 5:
            raise RateLimitException("Too many verification attempts. Please try again in 10 minutes.")
            
        ip_count = await redis_client.get(ip_key)
        if ip_count and int(ip_count) >= 10:
            raise RateLimitException("Too many verification attempts. Please try again in 10 minutes.")
            
        # Increment counters
        async with redis_client.pipeline() as pipe:
            if not phone_count:
                await pipe.set(phone_key, "1", ex=600)
            else:
                await pipe.incr(phone_key)
                
            if not ip_count:
                await pipe.set(ip_key, "1", ex=600)
            else:
                await pipe.incr(ip_key)
                
            await pipe.execute()
            
    except RateLimitException:
        raise
    except Exception as e:
        logger.error("redis_verify_rate_limiter_offline", error=str(e))

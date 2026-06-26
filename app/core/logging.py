import logging
import sys
import structlog
from app.core.config import settings

def setup_logging():
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.APP_ENV in ["production", "staging"]:
        # JSON structured logs for cloud environments (CloudWatch/Loki)
        processors = shared_processors + [
            structlog.processors.JSONRenderer()
        ]
        formatter = structlog.stdlib.ProcessorFormatter(
            processors=processors,
            foreign_pre_chain=shared_processors,
        )
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        
        root_logger = logging.getLogger()
        root_logger.handlers = [handler]
        root_logger.setLevel(logging.INFO if not settings.DEBUG else logging.DEBUG)
    else:
        # Readable, colored console logs for local development
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True)
        ]
        structlog.configure(
            processors=processors,
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG if settings.DEBUG else logging.INFO),
            cache_logger_on_first_use=True,
        )

    # Disable generic uvicorn access logging noise in production if not debug
    if settings.APP_ENV in ["production", "staging"] and not settings.DEBUG:
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    
    # Configure stdlib logging wrapper if any external libraries use it
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )

logger = structlog.get_logger()

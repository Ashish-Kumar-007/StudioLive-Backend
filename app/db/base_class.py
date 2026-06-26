import re
from typing import Any
from sqlalchemy.orm import DeclarativeBase, declared_attr


class Base(DeclarativeBase):
    id: Any
    __name__: str

    # Generate __tablename__ automatically in snake_case
    @declared_attr
    def __tablename__(cls) -> str:
        # Converts CamelCase class names to snake_case table names
        name = cls.__name__
        # Insert underscores before uppercase letters (except at start)
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        # Handle cases where multiple uppercase letters are adjacent (e.g. OTPState -> otp_state)
        s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
        
        # Add 's' suffix to pluralize unless it already ends with s/y/etc.
        if s2.endswith('y'):
            return s2[:-1] + 'ies'
        elif not s2.endswith('s'):
            return s2 + 's'
        return s2

from collections.abc import Iterable
from enum import Enum as PythonEnum

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def enum_values(enum_class: type[PythonEnum]) -> Iterable[str]:
    """Persist string enum values, matching the lowercase PostgreSQL types."""
    return [member.value for member in enum_class]

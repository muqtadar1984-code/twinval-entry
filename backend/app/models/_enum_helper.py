"""SQLAlchemy enum helper.

By default SQLAlchemy persists Python enums by their .name (UPPERCASE),
but our Postgres ENUM types are created with the lowercase .value strings
(matching the wire format used in the canonical hash payload). Pass
`values_callable=enum_values` to every Enum column so storage uses .value
instead of .name and stays consistent across SQLite (tests) and Postgres
(production).
"""

from enum import Enum
from typing import Type


def enum_values(enum_cls: Type[Enum]) -> list[str]:
    return [member.value for member in enum_cls]

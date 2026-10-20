
from dataclasses import dataclass


@dataclass(frozen=True)
class StudyAgentContext:
    """Trusted context supplied by the Django backend."""
    session_key: str

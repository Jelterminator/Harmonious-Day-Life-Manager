# File: src/models/api.py
"""
Data models for Harmonious Day API responses.
"""

from dataclasses import dataclass
from typing import Optional
from .schedule import Schedule

@dataclass
class LLMResponse:
    """Response from LLM API."""
    status: str  # "success" or "fail"
    schedule: Optional[Schedule] = None
    message: Optional[str] = None
    raw_response: Optional[dict] = None
    
    def is_success(self) -> bool:
        """Check if response was successful."""
        return self.status == "success" and self.schedule is not None


@dataclass
class ValidationError:
    """Represents a validation error."""
    field: str
    message: str
    entry_index: Optional[int] = None
    
    def __str__(self) -> str:
        """String representation of error."""
        if self.entry_index is not None:
            return f"Entry {self.entry_index} - {self.field}: {self.message}"
        return f"{self.field}: {self.message}"

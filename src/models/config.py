# File: src/models/config.py
"""
Data models for Harmonious Day configuration.
"""

from dataclasses import dataclass, field
from typing import List
from .phase import Phase

@dataclass
class PhaseConfig:
    """Configuration for a Wu Xing phase."""
    name: Phase
    start: str  # "HH:MM" format
    end: str    # "HH:MM" format
    qualities: str
    ideal_tasks: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Convert string name to enum, handling icons."""
        if isinstance(self.name, str):
            # Handle "🌳 WOOD" -> "WOOD"
            clean_name = self.name.split(' ')[-1] if ' ' in self.name else self.name
            try:
                self.name = Phase(clean_name)
            except ValueError:
                # Fallback if config has invalid phase name
                self.name = Phase.FIRE


@dataclass
class Anchor:
    """Spiritual/time anchor (e.g., prayer times)."""
    name: str
    time: str  # "HH:MM-HH:MM" format
    phase: Phase
    
    def __post_init__(self):
        """Convert string phase to enum."""
        if isinstance(self.phase, str):
            self.phase = Phase(self.phase)
    
    def get_start_end(self) -> tuple[str, str]:
        """Parse time range into start and end times."""
        if '-' in self.time:
            start, end = self.time.split('-')
            return start.strip(), end.strip()
        return self.time, self.time


@dataclass
class AppConfig:
    """Complete application configuration."""
    phases: List[PhaseConfig]
    anchors: List[Anchor]
    timezone: str = "UTC"
    max_output_tasks: int = 24
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AppConfig':
        """Create AppConfig from dictionary (e.g., loaded from JSON)."""
        phases = [PhaseConfig(**p) for p in data.get('phases', [])]
        anchors = [Anchor(**a) for a in data.get('anchors', [])]
        
        return cls(
            phases=phases,
            anchors=anchors,
            timezone=data.get('timezone', 'UTC'),
            max_output_tasks=data.get('max_output_tasks', 24)
        )

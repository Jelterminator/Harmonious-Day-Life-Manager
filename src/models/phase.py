# File: src/models/phase.py

from enum import Enum
from typing import Dict, List, Any, Union

class Phase(Enum):
    """Wu Xing phases of the day."""
    WOOD = "WOOD"    # 05:30-09:00 - Growth, planning
    FIRE = "FIRE"    # 09:00-13:00 - Peak energy
    EARTH = "EARTH"  # 13:00-15:00 - Grounding
    METAL = "METAL"  # 15:00-18:00 - Organization
    WATER = "WATER"  # 18:00-21:45 - Rest

# Consolidated Phase Metadata
# Combines logic from anchor_manager.py (ranges, qualities, tasks) and config_manager.py (colors)
PHASE_METADATA: Dict[Phase, Dict[str, Any]] = {
    Phase.WOOD: {
        "color": "10",
        "roman_range": [0, 1, 2, 21, 22, 23],
        "qualities": "Growth, Planning, Vitality. Spiritual centering & movement.",
        "tasks": ["spiritual", "planning", "movement"]
    },
    Phase.FIRE: {
        "color": "11",
        "roman_range": range(2, 6),
        "qualities": "Peak energy, expression. Deep work & execution.",
        "tasks": ["deep_work", "creative", "pomodoro"]
    },
    Phase.EARTH: {
        "color": "5",
        "roman_range": range(6, 8),
        "qualities": "Stability, nourishment. Lunch & restoration.",
        "tasks": ["rest", "integration", "light_tasks"]
    },
    Phase.METAL: {
        "color": "8",
        "roman_range": range(8, 12),
        "qualities": "Precision, organization. Admin & review.",
        "tasks": ["admin", "planning", "study"]
    },
    Phase.WATER: {
        "color": "9",
        "roman_range": range(12, 21),
        "qualities": "Rest, consolidation. Wind-down & recovery.",
        "tasks": ["rest", "reflection", "recovery"]
    }
}

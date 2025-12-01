# File: src/models/common

from datetime import datetime
from typing import Optional

def parse_iso_datetime(date_str: Optional[str]) -> Optional[datetime]:
    """Robustly parse ISO date strings with 'Z' or offsets."""
    if not date_str:
        return None
    try:
        # specific fix for Python < 3.11 which doesn't handle 'Z' natively in fromisoformat
        clean_str = date_str.replace('Z', '+00:00')
        return datetime.fromisoformat(clean_str)
    except ValueError:
        # Fallback for simple date strings without time
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return None

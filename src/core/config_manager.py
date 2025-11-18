# File: src/core/config_manager.py
"""
Centralized configuration management for Harmonious Day.
Loads settings from environment variables and config files.
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, Any, List
from dotenv import load_dotenv

# Import the new type models
from src.models.models import PriorityTier, Phase

# Load environment variables
load_dotenv()

class Config:
    """Application configuration singleton."""
    
    # Base directories
    BASE_DIR = Path(__file__).parent.parent.parent  # Go up 3 levels from src/core/
    
    # Subdirectories
    CONFIG_DIR = BASE_DIR / "config"
    OUTPUT_DIR = BASE_DIR / "output"
    LOGS_DIR = BASE_DIR / "logs"
    SRC_DIR = BASE_DIR / "src"
    
    # Files
    CONFIG_FILE = CONFIG_DIR / "config.json"
    SYSTEM_PROMPT_FILE = CONFIG_DIR / "system_prompt.txt"
    PROMPT_OUTPUT_FILE = OUTPUT_DIR / "last_world_prompt.txt"
    SCHEDULE_OUTPUT_FILE = OUTPUT_DIR / "generated_schedule.json"
    TOKEN_FILE = BASE_DIR / "token.json"
    CREDENTIALS_FILE = BASE_DIR / "credentials.json"
    ENV_FILE = BASE_DIR / ".env"
    
    # API Keys
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    
    # Google Services
    SHEET_ID = os.getenv("SHEET_ID", "1rdyKSYIT7NsIFtKg6UUeCnPEUUDtceKF3sfoVSwiaDM")
    HABIT_RANGE = "Habits!A:H"
    GOOGLE_SCOPES = [
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/tasks.readonly',
        'https://www.googleapis.com/auth/drive.metadata.readonly',
    ]

    
    # Application Settings
    TARGET_TIMEZONE = os.getenv("TIMEZONE", "Europe/Amsterdam")
    GENERATOR_ID = "AI_Harmonious_Day_Orchestrator_v1"
    MAX_OUTPUT_TASKS = 18
    
    # LLM Settings
    GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
    MODEL_ID = "openai/gpt-oss-20b"
    REASONING_EFFORT = "medium"
    MAX_COMPLETION_TOKENS = 32768
    
    # Priority Tiers (Derived from Enum)
    # Storing as string values for compatibility with other parts of the app
    PRIORITY_TIERS: List[str] = [p.value for p in PriorityTier]
    
    # Phase Color Mapping (Uses Enum values as keys)
    PHASE_COLORS: Dict[str, str] = {
        Phase.WOOD.value: '10',
        Phase.FIRE.value: '11',
        Phase.EARTH.value: '5',
        Phase.METAL.value: '8',
        Phase.WATER.value: '9'
    }
    
    DATE_PATTERNS = [
    # ISO and standard formats
    ("%Y-%m-%d", re.compile(r"^\d{4}-\d{2}-\d{2}$")),  # 2025-11-18
    ("%d-%m-%Y", re.compile(r"^\d{2}-\d{2}-\d{4}$")),  # 18-11-2025
    ("%d/%m/%Y", re.compile(r"^\d{2}/\d{2}/\d{4}$")),  # 18/11/2025
    ("%m/%d/%Y", re.compile(r"^\d{2}/\d{2}/\d{4}$")),  # 11/18/2025 (US format)
    ("%Y/%m/%d", re.compile(r"^\d{4}/\d{2}/\d{2}$")),  # 2025/11/18
    
    # Dot separators
    ("%d.%m.%Y", re.compile(r"^\d{2}\.\d{2}\.\d{4}$")),  # 18.11.2025
    ("%m.%d.%Y", re.compile(r"^\d{2}\.\d{2}\.\d{4}$")),  # 11.18.2025
    ("%Y.%m.%d", re.compile(r"^\d{4}\.\d{2}\.\d{2}$"))]  # 2025.11.18
    
    @classmethod
    def load_phase_config(cls) -> Dict[str, Any]:
        """Load phase configuration from JSON file."""
        if not cls.CONFIG_FILE.exists():
            raise FileNotFoundError(f"Config file not found: {cls.CONFIG_FILE}")
        
        with open(cls.CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @classmethod
    def validate(cls) -> bool:
        """Validate that all required configuration is present."""
        errors = []
        
        if not cls.GROQ_API_KEY:
            errors.append("GROQ_API_KEY not set")
        
        if not cls.CREDENTIALS_FILE.exists():
            errors.append(f"credentials.json not found at {cls.CREDENTIALS_FILE}")
        
        if not cls.CONFIG_FILE.exists():
            errors.append(f"config.json not found at {cls.CONFIG_FILE}")
        
        if errors:
            for error in errors:
                print(f"Configuration Error: {error}")
            return False
        
        return True
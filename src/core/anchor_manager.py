# Fukw: src/core/anchor_manager.py

import sqlite3
import json
import datetime
from pathlib import Path
from datetime import timedelta
import pytz

# Try to import astral, handle if missing (though setup.py should have installed it)
try:
    from astral import LocationInfo
    from astral.sun import sun
except ImportError:
    print("Error: 'astral' library not found. Please run scripts/setup.py again.")
    raise

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class AnchorManager:
    """
    Manages the calculation of dynamic daily anchors based on 
    Solar Roman Hours and user preferences stored in SQLite.
    """
    
    # Standard 5-element phase mapping to Roman Hours (0=Sunrise, 12=Sunset)
    PHASE_MAP = {
        "WOOD2":  {"range": range(0, 4),   "qualities": "Growth, Planning, Vitality. Spiritual centering & movement.", "tasks": ["spiritual", "planning", "movement"]},
        "FIRE":  {"range": range(4, 7),   "qualities": "Peak energy, expression. Deep work & execution.", "tasks": ["deep_work", "creative", "pomodoro"]},
        "EARTH": {"range": range(7, 9),   "qualities": "Stability, nourishment. Lunch & restoration.", "tasks": ["rest", "integration", "light_tasks"]},
        "METAL": {"range": range(9, 12),  "qualities": "Precision, organization. Admin & review.", "tasks": ["admin", "planning", "study"]},
        "WATER": {"range": range(12, 21), "qualities": "Rest, consolidation. vWind-down & recovery.", "tasks": ["rest", "reflection", "recovery"]},
        "WOOD1":  {"range": range(21, 24),   "qualities": "Growth, Planning, Vitality. Spiritual centering & movement.", "tasks": ["spiritual", "planning", "movement"]},
    }

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.db_path = project_root / "src" / "anchors.db"
        self.config_path = project_root / "config" / "config.json"
        
        # Ensure config dir exists
        self.config_path.parent.mkdir(exist_ok=True)

    def _get_db_connection(self):
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found at {self.db_path}. Run setup.py first.")
        return sqlite3.connect(self.db_path)

    def _get_location_settings(self):
        """Fetch lat/long/timezone from DB."""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM UserSettings")
        settings = dict(cursor.fetchall())
        conn.close()
        return settings

    def _calculate_roman_schedule(self, lat, lng, tz_name, date_obj):
        """Calculates solar Roman Hours for the specific date."""
        city = LocationInfo("UserLoc", "Region", tz_name, float(lat), float(lng))
        timezone = pytz.timezone(tz_name)
        
        s = sun(city.observer, date=date_obj, tzinfo=timezone)
        sunrise = s['sunrise']
        sunset = s['sunset']
        
        # Next day sunrise for night calculation
        s_next = sun(city.observer, date=date_obj + timedelta(days=1), tzinfo=timezone)
        next_sunrise = s_next['sunrise']
        
        day_duration = (sunset - sunrise).total_seconds()
        night_duration = (next_sunrise - sunset).total_seconds()
        
        day_hour_len = day_duration / 12
        night_hour_len = night_duration / 12
        
        schedule_map = {}
        
        # Daylight Hours (0-11)
        for h in range(0, 12):
            start = sunrise + timedelta(seconds=h * day_hour_len)
            end = sunrise + timedelta(seconds=(h + 1) * day_hour_len)
            schedule_map[h] = (start, end)

        # Night Hours (12-23)
        for h in range(12, 24):
            night_idx = h - 12
            start = sunset + timedelta(seconds=night_idx * night_hour_len)
            end = sunset + timedelta(seconds=(night_idx + 1) * night_hour_len)
            schedule_map[h] = (start, end)
            
        return schedule_map

    def _get_phase_for_hour(self, h):
        for phase_name, data in self.PHASE_MAP.items():
            if h in data['range']:
                return phase_name
        return "WATER"

    def generate_daily_config(self) -> bool:
        """
        Generates the config.json file with today's specific solar times.
        Returns: True if successful.
        """
        try:
            logger.info("Generating daily anchor configuration...")
            settings = self._get_location_settings()
            if not settings:
                logger.error("No location settings found in DB.")
                return False

            today = datetime.date.today()
            
            # 1. Calculate Grid
            time_grid = self._calculate_roman_schedule(
                settings.get('latitude', 52.01),
                settings.get('longitude', 4.35),
                settings.get('timezone', 'Europe/Amsterdam'),
                today
            )

            # 2. Fetch Active Practices
            conn = self._get_db_connection()
            cursor = conn.cursor()
            query = """
                SELECT p.name, p.roman_hour, p.duration_minutes, t.name as tradition
                FROM Practices p
                JOIN ActiveTraditions at ON p.tradition_id = at.tradition_id
                JOIN Traditions t ON p.tradition_id = t.id
                ORDER BY p.roman_hour ASC
            """
            cursor.execute(query)
            practices = cursor.fetchall()
            conn.close()

            # 3. Build Anchors
            anchors_list = []
            for name, hour, duration, tradition in practices:
                if hour in time_grid:
                    start_dt, end_hour_dt = time_grid[hour]
                    
                    # Calculate specific end time based on duration
                    if duration:
                        end_dt = start_dt + timedelta(minutes=duration)
                    else:
                        end_dt = end_hour_dt
                    
                    fmt = "%H:%M"
                    anchors_list.append({
                        "name": name,
                        "time": f"{start_dt.strftime(fmt)}-{end_dt.strftime(fmt)}",
                        "phase": self._get_phase_for_hour(hour).title(),
                        "tradition": tradition,
                        "roman_hour": hour
                    })

            # 4. Build Phases
            phases_list = []
            for phase_name in ["WOOD2", "FIRE", "EARTH", "METAL", "WATER", "WOOD1"]:
                data = self.PHASE_MAP[phase_name]
                hour_range = list(data['range'])
                
                # Dynamic start/end based on today's sun
                phase_start = time_grid[hour_range[0]][0]
                phase_end = time_grid[hour_range[-1]][1]
                
                phases_list.append({
                    "name": phase_name,
                    "start": phase_start.strftime("%H:%M"),
                    "end": phase_end.strftime("%H:%M"),
                    "qualities": data['qualities'],
                    "ideal_tasks": data['tasks']
                })

            # 5. Output
            final_json = {
                "date": str(today),
                "generated_at": datetime.datetime.now().isoformat(),
                "location": f"{settings.get('latitude')}, {settings.get('longitude')}",
                "phases": phases_list,
                "anchors": anchors_list
            }

            with open(self.config_path, 'w') as f:
                json.dump(final_json, f, indent=2)
            
            logger.info(f"Daily configuration written to {self.config_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to generate daily config: {e}", exc_info=True)
            return False
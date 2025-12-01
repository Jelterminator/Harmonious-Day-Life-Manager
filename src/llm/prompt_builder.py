# File: src/llm/prompt_builder.py
"""
Prompt building module for LLM scheduling requests.
Constructs the world prompt with all constraints and data.
"""

import datetime
import json
from typing import List, Dict, Any
from collections import defaultdict

from src.core.config_manager import Config
from src.utils.logger import setup_logger
# Import the typed models
from src.models import CalendarEvent, Task, Habit, PriorityTier, task_from_dict

logger = setup_logger(__name__)


class PromptBuilder:
    """Builds prompts for LLM schedule generation."""
    
    def __init__(self, rules: Dict[str, Any]):
        self.logger = logger  # FIX: logger must be assigned
        self.rules = rules    # FIX: rules stored for later use

        self.logger.info("PromptBuilder initialized")

    def build_world_prompt(
        self,
        calendar_events: List[CalendarEvent],  # Accepts typed CalendarEvent
        tasks: List[Task],                     # Accepts typed Task
        habits: List[Habit]                   # Accepts typed Habit
    ) -> str:
        """
        Build the complete world prompt for the LLM.
        
        Args:
            calendar_events: List of fixed CalendarEvent objects
            tasks: List of processed, prioritized Task objects
            habits: List of filtered Habit objects for today
        
        Returns:
            Complete world prompt string
        """
        self.logger.info("Building world prompt")
        import pytz
        
        local_tz = pytz.timezone(Config.TARGET_TIMEZONE)
        
        # Use a consistent timezone-aware 'now' for calculations
        now = datetime.datetime.now(datetime.timezone.utc).astimezone() 
        now_str = now.strftime("%Y-%m-%d %H:%M")
        today_date = now.date()
        tomorrow_date = today_date + datetime.timedelta(days=1)
        
        # Create proper end boundary
        end_of_tomorrow = datetime.datetime.combine(
            tomorrow_date, 
            datetime.time(23, 59)
        ).strftime("%Y-%m-%d %H:%M")
                
        prompt_lines = []
        
        # 1. HEADER & TIME WINDOW (FIXED)
        prompt_lines.append(f"SCHEDULE REQUEST")
        prompt_lines.append(f"CURRENT_TIME: {now_str}")
        prompt_lines.append(f"TODAY: {today_date.strftime('%Y-%m-%d')}")
        prompt_lines.append(f"TOMORROW: {tomorrow_date.strftime('%Y-%m-%d')}")
        prompt_lines.append(f"")
        prompt_lines.append(f"SCHEDULE_WINDOW: From {now_str} until {end_of_tomorrow}")
        prompt_lines.append(f"Do NOT schedule anything before {now_str}")
        prompt_lines.append(f"")
        prompt_lines.append(f"DATE_FIELD_INSTRUCTIONS:")
        prompt_lines.append(f"- Use 'today' in the date field for entries on {today_date.strftime('%Y-%m-%d')}")
        prompt_lines.append(f"- Use 'tomorrow' in the date field for entries on {tomorrow_date.strftime('%Y-%m-%d')}")
        prompt_lines.append(f"- Make sure start_time and end_time timestamps match the date field!")
        prompt_lines.append("")
        
        # 2. CRITICAL: SLEEP BOUNDARIES - for both days
        sleep_window = self.rules.get("sleep_window", {})
        if sleep_window:
            prompt_lines.append("=== CRITICAL: SLEEP BOUNDARIES (BOTH DAYS) ===")
            prompt_lines.append(f"Do NOT schedule ANY tasks between {sleep_window.get('start', '21:00')} and {sleep_window.get('end', '05:30')}")
            prompt_lines.append("")
        
        # 3. PHASE TIME BLOCKS - Separate sections for today and tomorrow
        prompt_lines.append("AVAILABLE PHASE WINDOWS:")
        prompt_lines.append("")
        
        # Group phases by date
        phases_by_date = {"today": [], "tomorrow": []}
        for p in self.rules.get("phases", []):
            date_key = p.get('date', 'today')
            if date_key in phases_by_date:
                phase_name = p['name']
                phases_by_date[date_key].append(p)
        
        # TODAY phases
        prompt_lines.append(f"TODAY ({today_date.strftime('%A')}):")
        if phases_by_date["today"]:
            for p in phases_by_date["today"]:
                prompt_lines.append(f"  {p['name']:6} | {p['start']} - {p['end']:8} | Tasks: {', '.join(p.get('ideal_tasks', []))}")
        prompt_lines.append("")
        
        # TOMORROW phases
        prompt_lines.append(f"TOMORROW ({tomorrow_date.strftime('%A')}):")
        if phases_by_date["tomorrow"]:
            for p in phases_by_date["tomorrow"]:
                prompt_lines.append(f"  {p['name']:6} | {p['start']} - {p['end']:8} | Tasks: {', '.join(p.get('ideal_tasks', []))}")
        prompt_lines.append("")
        
        # 4. STONES: Calendar Events (includes anchors and fixed events)
        prompt_lines.append("1. STONES: IMMOVABLE CALENDAR EVENTS")
        prompt_lines.append("(These occupy time and must NOT be overwritten)")
        prompt_lines.append("")
        
        if calendar_events:
            # Separate today and tomorrow events
            today_events = []
            tomorrow_events = []
            
            for e in calendar_events:
                event_dt = e.start.astimezone(local_tz)
                event_date = event_dt.date()
                
                if event_date == today_date:
                    today_events.append(e)
                elif event_date == tomorrow_date:
                    tomorrow_events.append(e)
            
            if today_events:
                prompt_lines.append(f"TODAY ({today_date.strftime('%A')}):")
                for e in sorted(today_events, key=lambda x: x.start):
                    start_fmt = e.start.astimezone(local_tz).strftime("%H:%M")
                    end_fmt = e.end.astimezone(local_tz).strftime("%H:%M")
                    marker = "[ANCHOR]" if "[ANCHOR]" in e.summary else "[FIXED]"
                    prompt_lines.append(f"  {start_fmt}-{end_fmt}: {e.summary} {marker}")
            
            if tomorrow_events:
                prompt_lines.append(f"TOMORROW ({tomorrow_date.strftime('%A')}):")
                for e in sorted(tomorrow_events, key=lambda x: x.start):
                    start_fmt = e.start.astimezone(local_tz).strftime("%H:%M")
                    end_fmt = e.end.astimezone(local_tz).strftime("%H:%M")
                    marker = "[ANCHOR]" if "[ANCHOR]" in e.summary else "[FIXED]"
                    prompt_lines.append(f"  {start_fmt}-{end_fmt}: {e.summary} {marker}")
            
            prompt_lines.append("")
            prompt_lines.append("CONSTRAINT: Schedule tasks ONLY in gaps between these events.")
            prompt_lines.append("Respect sleep boundaries (21:00-05:30).")
        else:
            prompt_lines.append("NONE - Full availability")
        
        prompt_lines.append("")
        
        # 5. PEBBLES: Urgent Tasks
        prompt_lines.append("2. PEBBLES: URGENT/DIFFICULT TASKS (T1-T5)")
        prompt_lines.append("(title|priority|effort_h|h_total|deadline|days_left|h_per_day|is_subtask|project_name|note)")
        prompt_lines.append("")
        
        pebbles_present = self._add_pebbles(prompt_lines, tasks)
        
        if not pebbles_present:
            prompt_lines.append("NONE")
        
        prompt_lines.append("")
        prompt_lines.append("STRATEGY: Schedule all urgent pebbles first.")
        prompt_lines.append("Spread across today and tomorrow to meet deadlines.")
        prompt_lines.append("DURATION FLEXIBILITY:")
        prompt_lines.append("  - Subtasks should be executed in numeric order as in the title")
        prompt_lines.append("  - Task durations CAN be reduced by up to 30% if needed to fit")
        prompt_lines.append("  - Task durations CAN be increased by up to 30% for deeper work")
        prompt_lines.append("  - Chunk large tasks: split 3+ hour tasks into multiple sessions broken up by habits and anchors")
        prompt_lines.append("  - It's OK to leave tasks partially done for tomorrow")
        prompt_lines.append("")
        
        # 6. SAND: Chores & Habits
        prompt_lines.append("3. SAND: CHORES (T6) & HABITS")
        prompt_lines.append("(Fill remaining time gaps with these)")
        prompt_lines.append("")
        
        self._add_chores(prompt_lines, tasks)
        self._add_habits(prompt_lines, habits)
        
        prompt_lines.append("")
        prompt_lines.append("STRATEGY:")
        prompt_lines.append("- Fill remaining gaps TODAY first")
        prompt_lines.append("- Fill remaining gaps TOMORROW second")
        prompt_lines.append("- Prioritize by: emotional wellbeing > reading > physical health")
        prompt_lines.append("- May skip habits if no time available")
        prompt_lines.append("DURATION FLEXIBILITY FOR HABITS:")
        prompt_lines.append("  - Habit durations CAN vary by ±50% (e.g., 30min habit → 15-45 min)")
        prompt_lines.append("  - Shorter versions are fine if time is tight")
        prompt_lines.append("  - Extended versions are fine if time is abundant")
        prompt_lines.append("  - Completely skip habits if the schedule is too packed")
        prompt_lines.append("")
        
        # 7. OUTPUT SCHEMA
        prompt_lines.append("OUTPUT REQUIREMENTS:")
        prompt_lines.append("- Return ONLY valid JSON (no markdown, no explanation)")
        prompt_lines.append("- Schedule entries for BOTH today and tomorrow where possible")
        prompt_lines.append("- Use date field: 'today' or 'tomorrow'")
        prompt_lines.append("- Ensure all times are in HH:MM format")
        prompt_lines.append("")
        
        try:
            from src.llm.client import OUTPUT_SCHEMA
            prompt_lines.append(json.dumps(OUTPUT_SCHEMA, indent=2))
        except ImportError:
            prompt_lines.append("JSON_SCHEMA_DEFINITION_HERE") 
        
        prompt = "\n".join(prompt_lines)
        
        pebble_count = sum(1 for t in tasks if t.priority != PriorityTier.T6)
        chore_count = sum(1 for t in tasks if t.priority == PriorityTier.T6)
        
        self.logger.info(f"World prompt built: {len(prompt)} characters")
        self.logger.debug(f"Prompt includes explicit scheduling for TODAY and TOMORROW")
        
        return prompt
    
    def _add_pebbles(
        self, 
        prompt_lines: List[str], 
        tasks: List[Task] # Uses typed Task list
    ) -> bool:
        """
        Add pebble tasks (T1-T5) to prompt.
        """
        pebbles_present = False
        
        # Group by priority
        by_priority = defaultdict(list)
        for t in tasks:
            if t.priority != PriorityTier.T6:
                by_priority[t.priority.value].append(t) # Use .value for string
                pebbles_present = True
        
        # Add in priority order
        for pr in sorted(by_priority.keys()):
            for t in by_priority[pr]:
                notes = t.notes or ""
                notes_clean = notes.replace("\n", " ").replace("|", "/").strip()
                title_clean = t.title.replace("|", "/").strip()
                # Use t.parent_title (assuming it was populated in TaskProcessor)
                parent_clean = str(t.parent_title or "").replace("|", "/").strip()
                
                line = "|".join([
                    title_clean,
                    t.priority.value, # Use .value
                    f"{t.effort_hours:.1f}",
                    f"{t.total_remaining_effort:.1f}",
                    f"{t.deadline_str}",
                    f"{t.days_until_deadline:.1f}",
                    f"{t.hours_per_day_needed:.1f}",
                    "1" if t.is_subtask else "0",
                    parent_clean,
                    notes_clean
                ])
                prompt_lines.append(line)
        
        return pebbles_present
    
    def _add_chores(self, prompt_lines: List[str], tasks: List[Task]) -> None: # Uses typed Task list
        """
        Add chore tasks (T6) to prompt.
        """
        chores = [t for t in tasks if t.priority == PriorityTier.T6]
        
        if chores:
            prompt_lines.append("CHORES (T6): (title|effort_h|notes)")
            for c in chores:
                title_clean = c.title.replace("|", "/").strip()
                notes = c.notes or ""
                prompt_lines.append(
                    f"{title_clean}|{c.effort_hours:.1f}|{notes}"
                )
        
    def _add_habits(self, prompt_lines: List[str], habits: List[Habit]) -> None: # Uses typed Habit list
        """
        Add habits to prompt.
        """
        if habits:
            prompt_lines.append("HABITS: (title|mins_ideal|ideal_phase)")
            for h in habits:
                prompt_lines.append("|".join([
                    h.title.replace("|", "/"),
                    str(h.duration_min),
                    h.ideal_phase.value # Use .value for string
                ]))
        
        if not habits and not any(t.priority == PriorityTier.T6 for t in tasks):
            prompt_lines.append("NONE")
    
    def save_prompt(self, prompt: str, filepath: str = None) -> None:
        """
        Save prompt to file for debugging.
        """
        if filepath is None:
            filepath = Config.PROMPT_OUTPUT_FILE
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(prompt)
            self.logger.info(f"Prompt saved to {filepath}")
        except Exception as e:
            self.logger.error(f"Failed to save prompt: {e}", exc_info=True)
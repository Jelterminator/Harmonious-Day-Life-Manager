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

logger = setup_logger(__name__)


class PromptBuilder:
    """Builds prompts for LLM schedule generation."""
    
    def __init__(self, rules: Dict[str, Any]):
        """
        Initialize prompt builder with scheduling rules.
        
        Args:
            rules: Dictionary containing phases and anchors from config.json
        """
        self.rules = rules
        self.logger = setup_logger(__name__)
    
    def build_world_prompt(
        self,
        calendar_events: List[Dict[str, str]],
        tasks: List[Dict[str, Any]],
        habits: List[Dict[str, Any]]
    ) -> str:
        """
        Build the complete world prompt for the LLM.
        
        Args:
            calendar_events: List of fixed calendar events
            tasks: List of processed, prioritized tasks
            habits: List of filtered habits for today
        
        Returns:
            Complete world prompt string
        """
        self.logger.info("Building world prompt")
        
        now = datetime.datetime.now()
        now_str = now.strftime("%Y-%m-%d %H:%M")
        today_date = now.date()
        tomorrow_date = today_date + datetime.timedelta(days=1)
        
        prompt_lines = []
        
        # 1. HEADER & TIME WINDOW
        prompt_lines.append(f"SCHEDULE REQUEST")
        prompt_lines.append(f"NOW: {now_str}")
        prompt_lines.append(f"SCHEDULE_WINDOW: {now_str} -> {tomorrow_date} 23:59")
        prompt_lines.append(f"SKIP_BEFORE: {now.strftime('%H:%M')}")
        prompt_lines.append("")
        
        # 2. PHASE TIME BLOCKS
        phase_parts = []
        for p in self.rules.get("phases", []):
            phase_name = p['name'].split()[0] if ' ' in p['name'] else p['name']
            phase_parts.append(f"{phase_name}:{p['start']}-{p['end']}")
        prompt_lines.append("PHASES: " + " | ".join(phase_parts))
        prompt_lines.append("")
        
        # 3. STONES: Calendar Events
        prompt_lines.append("1. STONES: IMMOVABLE CALENDAR EVENTS (summary|start|end)")
        if calendar_events:
            for e in calendar_events:
                prompt_lines.append(
                    f"{e.get('summary','-')}|{e.get('start')}|{e.get('end')}"
                )
            prompt_lines.append(
                "CONSTRAINT: Do not schedule ANY entry (Anchor, Pebble, or Sand) "
                "during Stone times."
            )
        else:
            prompt_lines.append("NONE")
        prompt_lines.append("")
        
        # 4. ANCHORS: Spiritual Commitments
        anchors = [f"{a['time']}:{a['name']}" for a in self.rules.get("anchors", [])]
        prompt_lines.append("2. ANCHORS: SPIRITUAL PRAYERS (time:name)")
        prompt_lines.append(" | ".join(anchors) if anchors else "NONE")
        prompt_lines.append(
            "CONSTRAINT: Schedule Anchors first. "
            "Must be skipped if blocked by a STONE."
        )
        prompt_lines.append("")
        
        # 5. PEBBLES: Urgent Tasks
        prompt_lines.append(
            "3. PEBBLES: URGENT/DIFFICULT TASKS (T1-T5) "
            "(title|priority|effort_h|total_remain_h|deadline|days_left|"
            "h_per_day|is_subtask|parent|notes)"
        )
        
        pebbles_present = self._add_pebbles(prompt_lines, tasks)
        
        if not pebbles_present:
            prompt_lines.append("NONE")
        
        prompt_lines.append("CONSTRAINTS:")
        prompt_lines.append(
            "Fit in many Pebbles (2-8 hours) after scheduling the Stones. "
            "To achieve this the duration can be reduced by maximally 25%."
        )
        prompt_lines.append(
            "Chunking: If effort_h > 2.0, then you may schedule the task in "
            "multiple blocks. It is okay to leave half finished tasks for the future."
        )
        prompt_lines.append(
            "When a parent task has numbered subtasks it is necessary to do "
            "the subtasks in the order of the numbering."
        )
        prompt_lines.append("")
        
        # 6. SAND: Chores & Habits
        prompt_lines.append("4. SAND: CHORES (T6) & HABITS (Fill remaining gaps)")
        
        self._add_chores(prompt_lines, tasks)
        self._add_habits(prompt_lines, habits)
        
        prompt_lines.append("CONSTRAINTS:")
        prompt_lines.append(
            "Only plan habits after the calendar is already filled with "
            "tasks & calendar events."
        )
        prompt_lines.append(
            "Like the sand entering the jar last and filling it to completion, "
            "fill all remaining spare time with habits."
        )
        prompt_lines.append(
            "Schedule habits near their correct Phase. Skipping habits is no problem "
            "at all. Durations may be changed up to 50%."
        )
        prompt_lines.append(
            "When choosing habits you firstly prioritise emotional wellbeing, "
            "secondly reading and thirdly physical health."
        )
        prompt_lines.append("")
        
        # 7. OUTPUT SCHEMA
        prompt_lines.append(
            "Return only JSON conforming to the following schema. "
            "Do not include reasoning."
        )
        
        from src.llm.client import OUTPUT_SCHEMA
        prompt_lines.append(json.dumps(OUTPUT_SCHEMA, indent=2))
        
        prompt = "\n".join(prompt_lines)
        
        self.logger.info(f"World prompt built: {len(prompt)} characters")
        self.logger.debug(f"Prompt includes: {len(calendar_events)} events, "
                         f"{sum(1 for t in tasks if t.get('priority') != 'T6')} pebbles, "
                         f"{sum(1 for t in tasks if t.get('priority') == 'T6')} chores, "
                         f"{len(habits)} habits")
        
        return prompt
    
    def _add_pebbles(
        self, 
        prompt_lines: List[str], 
        tasks: List[Dict[str, Any]]
    ) -> bool:
        """
        Add pebble tasks (T1-T5) to prompt.
        
        Args:
            prompt_lines: List to append lines to
            tasks: All tasks
        
        Returns:
            True if pebbles were added, False otherwise
        """
        pebbles_present = False
        
        # Group by priority
        by_priority = defaultdict(list)
        for t in tasks:
            if t.get('priority') != 'T6':
                by_priority[t['priority']].append(t)
                pebbles_present = True
        
        # Add in priority order
        for pr in sorted(by_priority.keys()):
            for t in by_priority[pr]:
                notes = t.get("notes") or ""
                notes_clean = notes.replace("\n", " ").replace("|", "/").strip()
                title_clean = t.get("title", "").replace("|", "/").strip()
                parent_clean = str(t.get("parent_title") or "").replace("|", "/").strip()
                
                line = "|".join([
                    title_clean,
                    pr,
                    f"{t.get('effort_hours', 0):.1f}",
                    f"{t.get('total_remaining_effort', 0):.1f}",
                    t.get("deadline_str", "N/A"),
                    f"{t.get('days_until_deadline', 0):.1f}",
                    f"{t.get('hours_per_day_needed', 0):.1f}",
                    "1" if t.get("is_subtask") else "0",
                    parent_clean,
                    notes_clean
                ])
                prompt_lines.append(line)
        
        return pebbles_present
    
    def _add_chores(self, prompt_lines: List[str], tasks: List[Dict[str, Any]]) -> None:
        """
        Add chore tasks (T6) to prompt.
        
        Args:
            prompt_lines: List to append lines to
            tasks: All tasks
        """
        chores = [t for t in tasks if t.get('priority') == 'T6']
        
        if chores:
            prompt_lines.append("CHORES (T6): (title|effort_h|notes)")
            for c in chores:
                title_clean = c.get("title", "").replace("|", "/").strip()
                notes = c.get("notes") or ""
                prompt_lines.append(
                    f"{title_clean}|{c.get('effort_hours', 0):.1f}|{notes}"
                )
    
    def _add_habits(self, prompt_lines: List[str], habits: List[Dict[str, Any]]) -> None:
        """
        Add habits to prompt.
        
        Args:
            prompt_lines: List to append lines to
            habits: Filtered habits for today
        """
        if habits:
            prompt_lines.append("HABITS: (title|mins_ideal|ideal_phase)")
            for h in habits:
                prompt_lines.append("|".join([
                    h.get("title", "").replace("|", "/"),
                    str(h.get("duration_min", "")),
                    str(h.get("ideal_phase", ""))
                ]))
        
        if not habits:
            prompt_lines.append("NONE")
    
    def save_prompt(self, prompt: str, filepath: str = None) -> None:
        """
        Save prompt to file for debugging.
        
        Args:
            prompt: Prompt text to save
            filepath: Optional custom filepath
        """
        if filepath is None:
            filepath = Config.PROMPT_OUTPUT_FILE
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(prompt)
            self.logger.info(f"Prompt saved to {filepath}")
        except Exception as e:
            self.logger.error(f"Failed to save prompt: {e}", exc_info=True)
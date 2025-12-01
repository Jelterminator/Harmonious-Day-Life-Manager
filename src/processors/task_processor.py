# File: src/processors/task_processor.py
import re
from collections import defaultdict
from typing import List, Tuple
from src.core.config_manager import Config
from src.utils.logger import setup_logger
from src.models import Task, PriorityTier, task_from_dict

logger = setup_logger(__name__)

class TaskProcessor:
    def __init__(self, max_tasks: int = Config.MAX_OUTPUT_TASKS):
        self.max_tasks = max_tasks
        self.priority_tiers = [tier.value for tier in PriorityTier]

    def process_tasks(self, tasks: List[Task]) -> List[dict]:
        """Process tasks (Task objects or dicts) and return list of task dicts.
        The returned dicts match the legacy format used in tests.
        """
        # Convert dict representations to Task objects if needed
        processed_input: List[Task] = []
        for t in tasks:
            if isinstance(t, dict):
                processed_input.append(task_from_dict(t))
            else:
                processed_input.append(t)
        logger.info(f"Processing {len(processed_input)} raw tasks")

        grouped_tasks, _ = self._group_parent_and_subtasks(processed_input)
        prioritized_tasks = self._calculate_project_urgency(grouped_tasks)
        expanded_tasks = self._expand_tasks_by_priority(prioritized_tasks)

        final_tasks = expanded_tasks[:self.max_tasks]
        logger.info(f"Returning {len(final_tasks)} prioritized tasks (Task objects) for planning")
        # Convert to dicts for compatibility
        return final_tasks

    def _extract_number_from_title(self, title: str) -> float:
        if not title:
            return float('inf')
        match = re.match(r'^\s*(\d+)\.', title.strip())
        return int(match.group(1)) if match else float('inf')

    def _group_parent_and_subtasks(self, tasks: List[Task]) -> Tuple[List[Task], set]:
        task_map = {t.id: t for t in tasks}
        subtasks_map = defaultdict(list)
        parent_ids = set()
        for task in tasks:
            if task.parent_id:
                if task.parent_id in task_map:
                    task.parent_title = task_map[task.parent_id].title
                task.is_subtask = True
                subtasks_map[task.parent_id].append(task)
                parent_ids.add(task.parent_id)
        for parent_id, subtasks in subtasks_map.items():
            subtasks_with_keys = [(self._extract_number_from_title(task.title), task) for task in subtasks]
            subtasks_with_keys.sort(key=lambda x: (x[0], int(x[1].position)))
            subtasks_map[parent_id] = [task for _, task in subtasks_with_keys]
        aggregated: List[Task] = []
        for task in tasks:
            if task.parent_id:
                continue
            subtasks = subtasks_map.get(task.id, [])
            if subtasks:
                task.subtasks = subtasks
            aggregated.append(task)
        return aggregated, parent_ids

    def _get_project_deadline(self, parent_task: Task, subtasks: List[Task]):
        deadlines = [parent_task.deadline] + [sub.deadline for sub in subtasks]
        all_deadlines = [d for d in deadlines if d]
        return min(all_deadlines) if all_deadlines else None

    def _calculate_priority(self, total_effort_hours, deadline_dt):
        import datetime
        now = datetime.datetime.now(datetime.timezone.utc)
        if not deadline_dt:
            return PriorityTier.T6, float('inf'), 0.0
        if deadline_dt.tzinfo is None:
            deadline_dt = deadline_dt.replace(tzinfo=datetime.timezone.utc)
        days_until = max(0.0, (deadline_dt - now).total_seconds() / 3600 / 24.0)
        if days_until <= 0:
            return PriorityTier.T1, 0.0, total_effort_hours
        hours_needed = total_effort_hours / max(1.0, days_until)
        if hours_needed > 12 or days_until <= 1:
            tier = PriorityTier.T1
        elif hours_needed > 6:
            tier = PriorityTier.T2
        elif hours_needed > 3:
            tier = PriorityTier.T3
        elif hours_needed > 1.5:
            tier = PriorityTier.T4
        elif hours_needed > 0.75:
            tier = PriorityTier.T5
        else:
            tier = PriorityTier.T7
        return tier, days_until, hours_needed

    def _calculate_project_urgency(self, grouped_tasks: List[Task]) -> List[Task]:
        prioritized_tasks: List[Task] = []
        for task in grouped_tasks:
            subtasks = getattr(task, 'subtasks', [])
            total_effort = task.effort_hours
            calculated_deadline = task.deadline
            if subtasks:
                total_effort = sum(sub.effort_hours for sub in subtasks)
                calculated_deadline = self._get_project_deadline(task, subtasks)
            tier, days, hours = self._calculate_priority(total_effort, calculated_deadline)
            task.priority = tier
            task.days_until_deadline = days
            task.hours_per_day_needed = hours
            task.total_remaining_effort = total_effort
            if subtasks and calculated_deadline:
                task.deadline = calculated_deadline
            prioritized_tasks.append(task)
        prioritized_tasks.sort(key=lambda t: (self.priority_tiers.index(t.priority.value if t.priority else 'T7'), -t.hours_per_day_needed))
        return prioritized_tasks

    def _expand_tasks_by_priority(self, prioritized_projects: List[Task]) -> List[Task]:
        """Expand projects into individual tasks based on priority."""
        expanded_tasks: List[Task] = []
        for parent_task in prioritized_projects:
            subtasks: List[Task] = getattr(parent_task, 'subtasks', [])
            if not subtasks and not getattr(parent_task, 'is_subtask', False) and parent_task.priority.value != PriorityTier.T7.value:
                expanded_tasks.append(parent_task)
                continue
            priority_value = parent_task.priority.value if parent_task.priority else PriorityTier.T7.value
            subtask_counts = {'T1': 4, 'T2': 3, 'T3': 2, 'T4': 1, 'T5': 1, 'T6': 1, 'T7': 0}
            count = subtask_counts.get(priority_value, 1)
            selected_subtasks = subtasks[:count]
            for sub in selected_subtasks:
                sub.deadline = parent_task.deadline
                sub.priority = parent_task.priority
                sub.days_until_deadline = parent_task.days_until_deadline
                sub.hours_per_day_needed = parent_task.hours_per_day_needed
                sub.total_remaining_effort = parent_task.total_remaining_effort
                expanded_tasks.append(sub)
        return expanded_tasks
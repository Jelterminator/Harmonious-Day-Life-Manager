# File: src/processors/task_processor.py (improved)
"""
Task processing module for Harmonious Day.

This module handles task prioritization, effort estimation, and deadline calculations
to prepare tasks for AI-powered scheduling.
"""

import datetime
import re
from collections import defaultdict
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass

from src.core.config_manager import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class TaskPriority:
    """Represents task priority calculation results."""
    tier: str
    days_until_deadline: float
    hours_per_day_needed: float


class TaskProcessor:
    """Processes raw tasks from Google Tasks into prioritized, schedulable items."""
    
    def __init__(self, max_tasks: int = Config.MAX_OUTPUT_TASKS):
        """
        Initialize the task processor.
        
        Args:
            max_tasks: Maximum number of tasks to return
        """
        self.max_tasks = max_tasks
        self.priority_tiers = Config.PRIORITY_TIERS
    
    def process_tasks(self, raw_tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process raw tasks into prioritized, schedulable format.
        
        Args:
            raw_tasks: List of raw task dictionaries from Google Tasks
        
        Returns:
            List of processed and prioritized tasks, limited to max_tasks
        """
        logger.info(f"Processing {len(raw_tasks)} raw tasks")
        
        grouped_tasks, parent_ids = self._group_parent_and_subtasks(raw_tasks)
        logger.debug(f"Grouped into {len(grouped_tasks)} parent tasks with subtasks")
        
        project_urgency = self._calculate_project_urgency(grouped_tasks)
        expanded_tasks = self._expand_tasks_by_priority(project_urgency)
        
        final_tasks = expanded_tasks[:self.max_tasks]
        logger.info(f"Returning {len(final_tasks)} prioritized tasks")
        
        return final_tasks
    
    def _extract_number_from_title(self, title: str) -> float:
        """
        Extract leading number from task title for subtask ordering.
        
        Args:
            title: Task title string
        
        Returns:
            Extracted number or float('inf') if not found
        
        Example:
            "01. First task" -> 1
            "10. Tenth task" -> 10
            "Task without number" -> inf
        """
        if not title:
            return float('inf')
        
        match = re.match(r'^\s*(\d+)\.', title.strip())
        return int(match.group(1)) if match else float('inf')
    
    def _group_parent_and_subtasks(
        self, 
        raw_tasks: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], set]:
        """
        Group tasks by parent-child relationships and sort subtasks.
        
        Args:
            raw_tasks: List of raw task dictionaries
        
        Returns:
            Tuple of (grouped tasks with subtasks, set of parent IDs)
        """
        task_map = {t['id']: t for t in raw_tasks}
        subtasks_map = defaultdict(list)
        parent_ids = set()
        
        # Collect subtasks for each parent
        for task in raw_tasks:
            if task.get('parent'):
                subtasks_map[task['parent']].append(task)
                parent_ids.add(task['parent'])
        
        # Sort subtasks by number prefix
        for parent_id, subtasks in subtasks_map.items():
            subtasks_with_keys = [
                (self._extract_number_from_title(task.get('title', '')), task)
                for task in subtasks
            ]
            subtasks_with_keys.sort(key=lambda x: (x[0], int(x[1].get('position', 0))))
            subtasks_map[parent_id] = [task for _, task in subtasks_with_keys]
        
        # Build aggregated task list
        aggregated = []
        processed_ids = set()
        
        for task in raw_tasks:
            if task['id'] in processed_ids or task.get('parent'):
                continue
            
            subtasks = subtasks_map.get(task['id'], [])
            for sub in subtasks:
                processed_ids.add(sub['id'])
            
            if subtasks:
                task['subtasks'] = subtasks
            
            aggregated.append(task)
            processed_ids.add(task['id'])
        
        return aggregated, parent_ids
    
    def _parse_effort(self, task: Dict[str, Any]) -> float:
        """
        Extract effort estimate from task title or notes.
        
        Args:
            task: Task dictionary
        
        Returns:
            Effort in hours (default: 1.0)
        
        Examples:
            Title: "Task name (2h)" -> 2.0
            Notes: "[Effort: 3.5h]" -> 3.5
        """
        title = task.get('title', '')
        title_match = re.search(r'\((\d+(?:\.\d+)?)[hu]\)', title, re.IGNORECASE)
        if title_match:
            return float(title_match.group(1))
        
        notes = task.get('notes') or ''
        effort_match = re.search(
            r'\[Effort:\s*(\d+(?:\.\d+)?)[hu]\]', 
            notes, 
            re.IGNORECASE
        )
        if effort_match:
            return float(effort_match.group(1))
        
        return 1.0
    
    def _parse_deadline(self, task: Dict[str, Any]) -> Optional[datetime.datetime]:
        """
        Parse deadline from task due date.
        
        Args:
            task: Task dictionary with 'due' field
        
        Returns:
            Deadline as timezone-aware datetime, or None if not set
        """
        due_str = task.get('due')
        if not due_str:
            return None
        
        try:
            if 'T' in due_str:
                return datetime.datetime.fromisoformat(due_str.replace('Z', '+00:00'))
            else:
                dt = datetime.datetime.strptime(due_str, '%Y-%m-%d')
                return dt.replace(
                    hour=23, 
                    minute=59, 
                    second=59, 
                    tzinfo=datetime.timezone.utc
                )
        except ValueError as e:
            logger.warning(f"Could not parse deadline '{due_str}': {e}")
            return None
    
    def _get_project_deadline(
        self, 
        parent_task: Dict[str, Any], 
        subtasks: List[Dict[str, Any]]
    ) -> Optional[datetime.datetime]:
        """
        Get earliest deadline from parent or any subtask.
        
        Args:
            parent_task: Parent task dictionary
            subtasks: List of subtask dictionaries
        
        Returns:
            Earliest deadline or None
        """
        parent_deadline = self._parse_deadline(parent_task)
        subtask_deadlines = [
            self._parse_deadline(sub) for sub in subtasks
        ]
        
        all_deadlines = [
            d for d in [parent_deadline] + subtask_deadlines if d
        ]
        
        return min(all_deadlines) if all_deadlines else None
    
    def _calculate_priority(
        self, 
        total_effort_hours: float, 
        deadline_dt: Optional[datetime.datetime]
    ) -> TaskPriority:
        """
        Calculate priority tier based on effort and deadline.
        
        Priority Tiers:
        - T1: >4 hours/day needed OR deadline within 1 day
        - T2: >2 hours/day needed
        - T3: >1 hour/day needed
        - T4: >0.5 hours/day needed
        - T5: >0.25 hours/day needed
        - T6: Lower priority tasks
        
        Args:
            total_effort_hours: Total estimated effort
            deadline_dt: Task deadline
        
        Returns:
            TaskPriority object with tier and metrics
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        
        if not deadline_dt:
            return TaskPriority('T6', float('inf'), 0)
        
        hours_until_deadline = (deadline_dt - now).total_seconds() / 3600
        days_until_deadline = hours_until_deadline / 24.0
        
        if days_until_deadline <= 0:
            return TaskPriority('T1', 0, total_effort_hours)
        
        hours_per_day_needed = (
            total_effort_hours if days_until_deadline <= 1
            else total_effort_hours / days_until_deadline
        )
        
        # Determine tier
        if hours_per_day_needed > 8 or days_until_deadline <= 1:
            tier = 'T1'
        elif hours_per_day_needed > 6:
            tier = 'T2'
        elif hours_per_day_needed > 4:
            tier = 'T3'
        elif hours_per_day_needed > 2:
            tier = 'T4'
        elif hours_per_day_needed > 1:
            tier = 'T5'
        else:
            tier = 'T7'
        
        return TaskPriority(tier, days_until_deadline, hours_per_day_needed)
    
    def _calculate_project_urgency(
        self, 
        grouped_tasks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Calculate urgency metrics for all tasks/projects.
        
        Args:
            grouped_tasks: List of parent tasks with optional subtasks
        
        Returns:
            List of project dictionaries sorted by urgency
        """
        project_urgency = []
        
        for task in grouped_tasks:
            subtasks = task.get('subtasks', [])
            
            if subtasks:
                total_effort = sum(self._parse_effort(sub) for sub in subtasks)
                deadline = self._get_project_deadline(task, subtasks)
            else:
                total_effort = self._parse_effort(task)
                deadline = self._parse_deadline(task)
            
            priority = self._calculate_priority(total_effort, deadline)
            
            project_urgency.append({
                'parent_task': task,
                'priority': priority.tier,
                'days_until_deadline': priority.days_until_deadline,
                'hours_per_day_needed': priority.hours_per_day_needed,
                'total_effort': total_effort,
                'all_subtasks': subtasks,
                'deadline_dt': deadline,
                'deadline_str': deadline.strftime("%Y-%m-%d") if deadline else "N/A"
            })
        
        # Sort by priority tier, then by hours per day needed
        project_urgency.sort(
            key=lambda p: (
                self.priority_tiers.index(p['priority']),
                -p['hours_per_day_needed']
            )
        )
        
        return project_urgency
    
    def _expand_tasks_by_priority(
        self, 
        project_urgency: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Expand projects into individual schedulable tasks based on priority.
        
        Priority determines how many subtasks to include:
        - T1: 4 subtasks
        - T2: 3 subtasks
        - T3: 2 subtasks
        - T4+: 1 subtask
        
        Args:
            project_urgency: List of projects sorted by urgency
        
        Returns:
            List of expanded tasks ready for scheduling
        """
        expanded_tasks = []
        
        for project in project_urgency:
            subtasks = project['all_subtasks']
            priority = project['priority']
            
            # Standalone task (no subtasks)
            if not subtasks:
                expanded_tasks.append({
                    **project['parent_task'],
                    'effort_hours': project['total_effort'],
                    'priority': priority,
                    'deadline_dt': project['deadline_dt'],
                    'deadline_str': project['deadline_str'],
                    'is_subtask': False,
                    'total_remaining_effort': project['total_effort'],
                    'days_until_deadline': project['days_until_deadline'],
                    'hours_per_day_needed': project['hours_per_day_needed']
                })
                continue
            
            # Determine subtask count by priority
            subtask_counts = {
                'T1': 4, 'T2': 3, 'T3': 2, 'T4': 1
            }
            count = subtask_counts.get(priority, 1)
            
            selected_subtasks = subtasks[:count]
            
            for sub in selected_subtasks:
                expanded_tasks.append({
                    **sub,
                    'effort_hours': self._parse_effort(sub),
                    'priority': priority,
                    'deadline_dt': project['deadline_dt'],
                    'deadline_str': project['deadline_str'],
                    'parent_title': project['parent_task'].get('title'),
                    'is_subtask': True,
                    'total_remaining_effort': project['total_effort'],
                    'days_until_deadline': project['days_until_deadline'],
                    'hours_per_day_needed': project['hours_per_day_needed']
                })
        
        return expanded_tasks


# Backward compatibility function
def process_tasks(raw_tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Process tasks (backward compatibility wrapper).
    
    Args:
        raw_tasks: List of raw task dictionaries
    
    Returns:
        List of processed tasks
    """
    processor = TaskProcessor()
    return processor.process_tasks(raw_tasks)
# File: task?processor.py
import datetime
import re
from collections import defaultdict

# --- NEW CONSTANT ---
MAX_OUTPUT_TASKS = 24

PRIORITY_TIERS = ['T1','T2','T3','T4','T5','T6','T7']

# --- HELPERS ---

def extract_number_from_title(title):
    if not title:
        return float('inf')
    match = re.match(r'^\s*(\d+)\.', title.strip())
    if match:
        return int(match.group(1))
    return float('inf')


def group_parent_and_subtasks(raw_tasks):
    task_map = {t['id']: t for t in raw_tasks}
    subtasks_map = defaultdict(list)
    parent_ids = set()
    
    for t in raw_tasks:
        if t.get('parent'):
            subtasks_map[t['parent']].append(t)
            parent_ids.add(t['parent'])
    
    for parent_id in subtasks_map:
        subtasks = subtasks_map[parent_id]
        subtasks_with_keys = []
        for task in subtasks:
            task_number = extract_number_from_title(task.get('title', ''))
            subtasks_with_keys.append((task_number, task))
        
        subtasks_with_keys.sort(key=lambda x: (x[0], int(x[1].get('position', 0))))
        subtasks_map[parent_id] = [task for _, task in subtasks_with_keys]
    
    aggregated = []
    processed_ids = set()
    
    for t in raw_tasks:
        if t['id'] in processed_ids:
            continue
        if t.get('parent'):
            continue
        
        subtasks = subtasks_map.get(t['id'], [])
        for sub in subtasks:
            processed_ids.add(sub['id'])
            
        if subtasks:
            t['subtasks'] = subtasks
        aggregated.append(t)
        processed_ids.add(t['id'])
    
    return aggregated, parent_ids


def parse_effort(task):
    title = task.get('title', '')
    title_match = re.search(r'\((\d+(?:\.\d+)?)[hu]\)', title, re.IGNORECASE)
    if title_match:
        return float(title_match.group(1))
    
    notes = task.get('notes') or ''
    effort_match = re.search(r'\[Effort:\s*(\d+(?:\.\d+)?)[hu]\]', notes, re.IGNORECASE)
    if effort_match:
        return float(effort_match.group(1))
    
    return 1.0


def parse_deadline(task):
    due_str = task.get('due')
    if due_str:
        try:
            if 'T' in due_str:
                return datetime.datetime.fromisoformat(due_str.replace('Z', '+00:00'))
            else:
                dt = datetime.datetime.strptime(due_str, '%Y-%m-%d')
                return dt.replace(hour=23, minute=59, second=59, tzinfo=datetime.timezone.utc)
        except ValueError:
            pass
    return None


def get_project_deadline(parent_task, subtasks):
    parent_deadline = parse_deadline(parent_task)
    subtask_deadlines = [parse_deadline(sub) for sub in subtasks]
    subtask_deadlines = [d for d in subtask_deadlines if d]
    all_deadlines = [d for d in [parent_deadline] + subtask_deadlines if d]
    return min(all_deadlines) if all_deadlines else None


def calculate_priority(total_effort_hours, deadline_dt):
    now = datetime.datetime.now(datetime.timezone.utc)
    
    if not deadline_dt:
        return 'T6', float('inf'), 0
    
    hours_until_deadline = (deadline_dt - now).total_seconds() / 3600
    days_until_deadline = hours_until_deadline / 24.0
    
    if days_until_deadline <= 0:
        return 'T1', 0, total_effort_hours
    
    if days_until_deadline <= 1:
        hours_per_day_needed = total_effort_hours
    else:
        hours_per_day_needed = total_effort_hours / days_until_deadline
    
    if hours_per_day_needed > 4 or days_until_deadline <= 1:
        return 'T1', days_until_deadline, hours_per_day_needed
    elif hours_per_day_needed > 2:
        return 'T2', days_until_deadline, hours_per_day_needed
    elif hours_per_day_needed > 1:
        return 'T3', days_until_deadline, hours_per_day_needed
    elif hours_per_day_needed > 0.5:
        return 'T4', days_until_deadline, hours_per_day_needed
    elif hours_per_day_needed > 0.25:
        return 'T5', days_until_deadline, hours_per_day_needed
    else:
        return 'T7', days_until_deadline, hours_per_day_needed


# --- MAIN PROCESSOR ---

def process_tasks(raw_tasks):
    grouped_tasks, parent_ids = group_parent_and_subtasks(raw_tasks)

    project_urgency = []

    for task in grouped_tasks:
        if task.get('subtasks'):
            subtasks = task['subtasks']
            total_subtask_effort = sum(parse_effort(sub) for sub in subtasks)
            project_deadline = get_project_deadline(task, subtasks)
            priority, days_left, hours_per_day = calculate_priority(total_subtask_effort, project_deadline)

            project_urgency.append({
                'parent_task': task,
                'priority': priority,
                'days_until_deadline': days_left,
                'hours_per_day_needed': hours_per_day,
                'total_effort': total_subtask_effort,
                'all_subtasks': subtasks,
                'deadline_dt': project_deadline,
                'deadline_str': project_deadline.strftime("%Y-%m-%d") if project_deadline else "N/A"
            })
        else:
            effort = parse_effort(task)
            deadline = parse_deadline(task)
            priority, days_left, hours_per_day = calculate_priority(effort, deadline)
            
            project_urgency.append({
                'parent_task': task,
                'priority': priority,
                'days_until_deadline': days_left,
                'hours_per_day_needed': hours_per_day,
                'total_effort': effort,
                'all_subtasks': [],
                'deadline_dt': deadline,
                'deadline_str': deadline.strftime("%Y-%m-%d") if deadline else "N/A"
            })

    # Sort by urgency
    project_urgency.sort(key=lambda p: (
        PRIORITY_TIERS.index(p['priority']), 
        -p['hours_per_day_needed']
    ))

    # --- NEW LOGIC: NO CAPACITY CALCULATION ---
    # We simply expand tasks according to priority tier
    expanded_tasks = []

    for project in project_urgency:
        subtasks = project['all_subtasks']
        priority = project['priority']

        if len(subtasks) == 0:
            # Standalone task → add as single entry
            effort = parse_effort(project['parent_task'])
            expanded_tasks.append({
                **project['parent_task'],
                'effort_hours': effort,
                'priority': priority,
                'deadline_dt': project['deadline_dt'],
                'deadline_str': project['deadline_str'],
                'is_subtask': False
            })
            continue

        # --- PRIORITY SUBTASK COUNT RULES ---
        if priority == 'T1':
            count = 5
        elif priority == 'T2':
            count = 3
        elif priority in ['T3', 'T4']:
            count = 2
        else:
            count = 1  # T5/T6/T7

        selected_subtasks = subtasks[:count]

        for sub in selected_subtasks:
            expanded_tasks.append({
                **sub,
                'effort_hours': parse_effort(sub),
                'priority': priority,
                'deadline_dt': project['deadline_dt'],
                'deadline_str': project['deadline_str'],
                'parent_title': project['parent_task'].get('title'),
                'is_subtask': True
            })

    # --- FINAL LIMIT: ONLY TOP 16 ---
    return expanded_tasks[:MAX_OUTPUT_TASKS]

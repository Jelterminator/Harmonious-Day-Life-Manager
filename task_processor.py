import datetime
import re
from collections import defaultdict

# --- CONFIG ---
MAX_EFFORT_HOURS_FOR_AI = 10  # max hours to schedule tasks in a day

# New priority tiers based on Critical Ratio + effort weight
PRIORITY_TIERS = ['T1','T2','T3','T4','T5','T6','T7']

# --- HELPERS ---

def group_parent_and_subtasks(raw_tasks):
    """Group subtasks under their parent and aggregate total effort."""
    task_map = {t['id']: t for t in raw_tasks}
    subtasks_map = defaultdict(list)
    for t in raw_tasks:
        if t.get('parent'):
            subtasks_map[t['parent']].append(t)
    aggregated = []
    for t in raw_tasks:
        if t.get('parent'):
            continue
        subtasks = subtasks_map.get(t['id'], [])
        if subtasks:
            t['subtasks'] = subtasks
        aggregated.append(t)
    return aggregated

def parse_effort(task):
    """Extract effort in hours from task notes or default to 1h."""
    notes = task.get('notes') or ''
    effort_hours = 0.0

    effort_match = re.search(r'\[Effort:\s*(\d+[hu]\s*(\d+m)?|\d+\.\d+[hu])\]', notes, re.IGNORECASE)
    if effort_match:
        effort_str = effort_match.group(1).lower().replace(' ', '')
        h = m = 0
        if 'h' in effort_str:
            h_match = re.search(r'(\d+)h', effort_str)
            if h_match:
                h = int(h_match.group(1))
        if 'm' in effort_str:
            m_match = re.search(r'(\d+)m', effort_str)
            if m_match:
                m = int(m_match.group(1))
        effort_hours = h + m / 60.0
    if effort_hours == 0.0:
        effort_hours = 1.0
    return effort_hours

def parse_deadline(task):
    """Parse deadline string to datetime or None."""
    due_str = task.get('due')
    if not due_str:
        return None
    try:
        if 'T' in due_str:
            return datetime.datetime.fromisoformat(due_str.replace('Z', '+00:00'))
        else:
            dt = datetime.datetime.strptime(due_str, '%Y-%m-%d')
            return dt.replace(hour=23, minute=59, second=59, tzinfo=datetime.timezone.utc)
    except ValueError:
        return None

def calculate_priority(effort_hours, deadline_dt):
    """Compute priority T1-T7 using weighted Critical Ratio and effort."""
    now = datetime.datetime.now(datetime.timezone.utc)
    
    if not deadline_dt:
        # No deadline → mid-priority
        return 'T4', None

    hours_left = (deadline_dt - now).total_seconds() / 3600
    if hours_left <= 0:
        return 'T1', 0  # past due

    cr = hours_left / effort_hours  # Critical Ratio

    # Weighted criteria: smaller effort or near deadline → higher priority
    if cr < 2.0:
        return 'T1', cr
    elif cr < 4.0:
        return 'T2', cr
    elif cr < 8.0:
        return 'T3', cr
    elif cr < 16.0:
        return 'T4', cr
    elif cr < 32.0:
        return 'T5', cr
    elif cr < 64.0:
        return 'T6', cr
    else:
        return 'T7', cr

# --- MAIN PROCESSOR ---

def process_tasks(raw_tasks, max_hours=MAX_EFFORT_HOURS_FOR_AI):
    """Aggregate, prioritize, and select only executable tasks for scheduling."""
    grouped_tasks = group_parent_and_subtasks(raw_tasks)
    processed = []

    for task in grouped_tasks:
        # Skip parent if it has subtasks — only include subtasks
        if task.get('subtasks'):
            for sub in task['subtasks']:
                effort = parse_effort(sub)
                deadline = parse_deadline(sub)
                priority, cr = calculate_priority(effort, deadline)
                processed.append({
                    **sub,
                    'effort_hours': effort,
                    'deadline_dt': deadline,
                    'priority': priority,
                    'critical_ratio': cr
                })
        else:
            effort = parse_effort(task)
            deadline = parse_deadline(task)
            priority, cr = calculate_priority(effort, deadline)
            processed.append({
                **task,
                'effort_hours': effort,
                'deadline_dt': deadline,
                'priority': priority,
                'critical_ratio': cr
            })


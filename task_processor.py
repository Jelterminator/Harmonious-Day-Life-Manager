import datetime
import re
from collections import defaultdict

# --- CONFIG ---
MAX_EFFORT_HOURS_FOR_AI = 12  # max hours to schedule tasks in a day

# Priority tiers based on Critical Ratio + effort weight
PRIORITY_TIERS = ['T1','T2','T3','T4','T5','T6','T7']

# --- HELPERS ---

def group_parent_and_subtasks(raw_tasks):
    """
    FIXED: Ensure subtasks maintain their proper sequential order using position field.
    """
    task_map = {t['id']: t for t in raw_tasks}
    subtasks_map = defaultdict(list)
    parent_ids = set()
    
    # First pass: group subtasks under parents
    for t in raw_tasks:
        if t.get('parent'):
            subtasks_map[t['parent']].append(t)
            parent_ids.add(t['parent'])
    
    # CRITICAL FIX: Sort subtasks by position (Google Tasks order)
    for parent_id in subtasks_map:
        # Convert position to integer for proper sorting
        subtasks_map[parent_id].sort(key=lambda x: int(x.get('position', 0)))
    
    aggregated = []
    processed_ids = set()
    
    # Second pass: build aggregated list with proper ordering
    for t in raw_tasks:
        if t['id'] in processed_ids:
            continue
            
        if t.get('parent'):
            # Skip subtasks here; they'll be added under their parents
            continue
            
        subtasks = subtasks_map.get(t['id'], [])
        # Mark subtasks as processed
        for sub in subtasks:
            processed_ids.add(sub['id'])
            
        if subtasks:
            t['subtasks'] = subtasks
        aggregated.append(t)
        processed_ids.add(t['id'])
    
    return aggregated, parent_ids

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

def calculate_priority(total_effort_hours, deadline_dt):
    """
    Compute priority T1-T7 based on total remaining effort vs time until deadline.
    
    FIXED: Now properly calculates how many hours per day are needed to complete
    ALL remaining work before the deadline.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    
    if not deadline_dt:
        return 'T7', float('inf'), 0
    
    hours_until_deadline = (deadline_dt - now).total_seconds() / 3600
    days_until_deadline = hours_until_deadline / 24.0
    
    # Past due - MAXIMUM URGENCY
    if days_until_deadline <= 0:
        return 'T1', 0, total_effort_hours
    
    # CRITICAL FIX: Calculate realistic hours per day needed
    # Assuming 8 productive hours per day maximum
    if days_until_deadline <= 1:
        # Due tomorrow or today - need to work ALL remaining hours today
        hours_per_day_needed = total_effort_hours
    else:
        # Spread over available days, but cap at 8h/day maximum sustainable
        hours_per_day_needed = total_effort_hours / days_until_deadline
    
    # Priority based on daily effort required - UPDATED THRESHOLDS
    if hours_per_day_needed > 8 or days_until_deadline <= 1:
        # Need more than 8h/day OR due within 1 day = CRITICAL
        return 'T1', days_until_deadline, hours_per_day_needed
    elif hours_per_day_needed > 6:
        # Need 6-8h/day = HIGH urgency  
        return 'T2', days_until_deadline, hours_per_day_needed
    elif hours_per_day_needed > 4:
        # Need 4-6h/day = MODERATE urgency
        return 'T3', days_until_deadline, hours_per_day_needed
    elif hours_per_day_needed > 2:
        return 'T4', days_until_deadline, hours_per_day_needed
    elif hours_per_day_needed > 1:
        return 'T5', days_until_deadline, hours_per_day_needed
    else:
        return 'T6', days_until_deadline, hours_per_day_needed

# --- MAIN PROCESSOR ---

def process_tasks(raw_tasks, max_hours=MAX_EFFORT_HOURS_FOR_AI):
    """
    FIXED: Properly identifies and shows only the FIRST incomplete subtask of each project,
    while prioritizing projects based on overall urgency.
    """
    # First, let's debug what we're receiving
    print(f"DEBUG: Received {len(raw_tasks)} raw tasks")
    for i, task in enumerate(raw_tasks):
        print(f"  {i}: '{task.get('title', 'No title')}' - parent: {task.get('parent')} - id: {task['id']}")

    grouped_tasks, parent_ids = group_parent_and_subtasks(raw_tasks)
    print(f"DEBUG: Found {len(grouped_tasks)} grouped tasks, {len(parent_ids)} parent IDs")
    
    processed = []
    project_urgency = []

    for task in grouped_tasks:
        if task.get('subtasks'):
            # Calculate TOTAL effort for ALL remaining subtasks
            total_subtask_effort = sum(parse_effort(sub) for sub in task['subtasks'])
            
            # Get the parent's deadline
            parent_deadline = parse_deadline(task)
            if not parent_deadline:
                # Use earliest subtask deadline
                subtask_deadlines = [parse_deadline(sub) for sub in task['subtasks']]
                subtask_deadlines = [d for d in subtask_deadlines if d]
                parent_deadline = min(subtask_deadlines) if subtask_deadlines else None
            
            # Calculate priority based on TOTAL remaining work
            priority, days_left, hours_per_day = calculate_priority(total_subtask_effort, parent_deadline)
            
            # CRITICAL: Only take the FIRST subtask
            first_subtask = task['subtasks'][0]
            
            project_urgency.append({
                'parent_task': task,
                'priority': priority,
                'days_until_deadline': days_left,
                'hours_per_day_needed': hours_per_day,
                'total_effort': total_subtask_effort,
                'first_subtask': first_subtask,
                'deadline_str': parent_deadline.strftime("%Y-%m-%d") if parent_deadline else "N/A",
                'all_subtasks': task['subtasks']  # Keep for debugging
            })
            
        else:
            # Standalone task
            effort = parse_effort(task)
            deadline = parse_deadline(task)
            priority, days_left, hours_per_day = calculate_priority(effort, deadline)
            
            project_urgency.append({
                'parent_task': task,
                'priority': priority,
                'days_until_deadline': days_left,
                'hours_per_day_needed': hours_per_day,
                'total_effort': effort,
                'first_subtask': None,  # Mark as standalone
                'deadline_str': deadline.strftime("%Y-%m-%d") if deadline else "N/A"
            })

    # Sort by urgency (priority first, then hours needed per day)
    project_urgency.sort(key=lambda p: (
        PRIORITY_TIERS.index(p['priority']), 
        -p['hours_per_day_needed']
    ))

    # Debug: Show what we found
    print(f"\nDEBUG: Project urgency ranking:")
    for i, project in enumerate(project_urgency):
        if project['first_subtask']:
            print(f"  {i}: {project['priority']} - '{project['first_subtask'].get('title')}' (from '{project['parent_task'].get('title')}')")
        else:
            print(f"  {i}: {project['priority']} - '{project['parent_task'].get('title')}' (standalone)")

    # Build final task list
    total_hours = 0
    for project in project_urgency:
        if total_hours >= max_hours:
            break
            
        if project['first_subtask']:
            # This is a project with subtasks - use the FIRST one only
            first_sub = project['first_subtask']
            first_sub_effort = parse_effort(first_sub)
            
            if total_hours + first_sub_effort <= max_hours:
                processed.append({
                    **first_sub,
                    'effort_hours': first_sub_effort,
                    'deadline_dt': parse_deadline(project['parent_task']),
                    'priority': project['priority'],
                    'days_until_deadline': project['days_until_deadline'],
                    'hours_per_day_needed': project['hours_per_day_needed'],
                    'deadline_str': project['deadline_str'],
                    'parent_title': project['parent_task'].get('title', 'Unknown'),
                    'total_remaining_effort': project['total_effort'],
                    'remaining_subtasks': len(project['all_subtasks']),
                    'is_subtask': True
                })
                total_hours += first_sub_effort
        else:
            # Standalone task
            effort = parse_effort(project['parent_task'])
            if total_hours + effort <= max_hours:
                processed.append({
                    **project['parent_task'],
                    'effort_hours': effort,
                    'deadline_dt': parse_deadline(project['parent_task']),
                    'priority': project['priority'],
                    'days_until_deadline': project['days_until_deadline'],
                    'hours_per_day_needed': project['hours_per_day_needed'],
                    'deadline_str': project['deadline_str'],
                    'parent_title': None,
                    'total_remaining_effort': effort,
                    'remaining_subtasks': 1,
                    'is_subtask': False
                })
                total_hours += effort

    print(f"DEBUG: Final processed tasks: {len(processed)}")
    return processed

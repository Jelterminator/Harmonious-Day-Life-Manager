import datetime
import re
from collections import defaultdict

# --- CONFIG ---
MAX_URGENT_TASKS = 7  # Aantal "Stones" (T1-T5) om aan de AI te geven
MAX_CHORE_TASKS = 3   # Aantal "Sand" (T6-T7) om te garanderen dat klusjes meegaan

# Priority tiers based on Critical Ratio + effort weight
PRIORITY_TIERS = ['T1','T2','T3','T4','T5','T6','T7']

# --- HELPERS ---

def extract_number_from_title(title):
    """
    Extraheert een numerieke sorteersleutel uit taaktitels.
    Retourneert float('inf') als er geen nummer is gevonden.
    """
    if not title:
        return float('inf')
    
    # Zoek naar patroon "01. Taaknaam" aan het begin
    match = re.match(r'^\s*(\d+)\.', title.strip())
    if match:
        return int(match.group(1))
    
    return float('inf')  # Geen nummer gevonden = zet aan het einde

def group_parent_and_subtasks(raw_tasks):
    """
    Groepeert sub-taken onder ouders en sorteert ze op nummer in titel.
    """
    task_map = {t['id']: t for t in raw_tasks}
    subtasks_map = defaultdict(list)
    parent_ids = set()
    
    # 1. Groepeer sub-taken onder ouders
    for t in raw_tasks:
        if t.get('parent'):
            subtasks_map[t['parent']].append(t)
            parent_ids.add(t['parent'])
    
    # 2. Sorteer sub-taken op nummer in titel
    for parent_id in subtasks_map:
        subtasks = subtasks_map[parent_id]
        
        # Sorteer op geëxtraheerd nummer, dan op positie
        subtasks_with_keys = []
        for task in subtasks:
            task_number = extract_number_from_title(task.get('title', ''))
            subtasks_with_keys.append((task_number, task))
        
        subtasks_with_keys.sort(key=lambda x: (x[0], int(x[1].get('position', 0))))
        subtasks_map[parent_id] = [task for _, task in subtasks_with_keys]
    
    # 3. Bouw geaggregeerde lijst
    aggregated = []
    processed_ids = set()
    
    for t in raw_tasks:
        if t['id'] in processed_ids:
            continue
            
        if t.get('parent'):
            continue  # Skip sub-taken, worden toegevoegd onder ouders
            
        subtasks = subtasks_map.get(t['id'], [])
        for sub in subtasks:
            processed_ids.add(sub['id'])
            
        if subtasks:
            t['subtasks'] = subtasks
        aggregated.append(t)
        processed_ids.add(t['id'])
    
    return aggregated, parent_ids

def parse_effort(task):
    """Extraheert inspanning in uren uit taaktitel of notities."""
    # Eerst titel controleren op patronen zoals "Taaknaam (3u)"
    title = task.get('title', '')
    title_match = re.search(r'\((\d+(?:\.\d+)?)[hu]\)', title, re.IGNORECASE)
    if title_match:
        return float(title_match.group(1))
    
    # Dan notities controleren op [Effort: ...] formaat
    notes = task.get('notes') or ''
    effort_match = re.search(r'\[Effort:\s*(\d+(?:\.\d+)?)[hu]\]', notes, re.IGNORECASE)
    if effort_match:
        return float(effort_match.group(1))
    
    # Standaard naar 1 uur als geen inspanning gespecificeerd
    return 1.0

def parse_deadline(task):
    """Parse deadline van taak's due datum."""
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
    """
    Krijgt de meest urgente deadline (vroegste datum) van een project.
    Checkt de ouder-taak en alle sub-taken.
    """
    parent_deadline = parse_deadline(parent_task)
    subtask_deadlines = [parse_deadline(sub) for sub in subtasks]
    subtask_deadlines = [d for d in subtask_deadlines if d]
    
    all_deadlines = [d for d in [parent_deadline] + subtask_deadlines if d]
    
    return min(all_deadlines) if all_deadlines else None

def calculate_priority(total_effort_hours, deadline_dt):
    """
    Berekent prioriteit T1-T7 gebaseerd op 'uren per dag nodig'.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    
    if not deadline_dt:
        return 'T7', float('inf'), 0  # Geen deadline
    
    hours_until_deadline = (deadline_dt - now).total_seconds() / 3600
    days_until_deadline = hours_until_deadline / 24.0
    
    if days_until_deadline <= 0:
        return 'T1', 0, total_effort_hours  # Te laat
    
    # Bereken realistisch benodigde uren per dag
    if days_until_deadline <= 1:
        hours_per_day_needed = total_effort_hours
    else:
        hours_per_day_needed = total_effort_hours / days_until_deadline
    
    # Prioriteit gebaseerd op dagelijkse inspanning
    if hours_per_day_needed > 8 or days_until_deadline <= 1:
        return 'T1', days_until_deadline, hours_per_day_needed
    elif hours_per_day_needed > 6:
        return 'T2', days_until_deadline, hours_per_day_needed
    elif hours_per_day_needed > 4:
        return 'T3', days_until_deadline, hours_per_day_needed
    elif hours_per_day_needed > 2:
        return 'T4', days_until_deadline, hours_per_day_needed
    elif hours_per_day_needed > 1:
        return 'T5', days_until_deadline, hours_per_day_needed
    else:
        return 'T6', days_until_deadline, hours_per_day_needed

# --- MAIN PROCESSOR ---

def process_tasks(raw_tasks):
    """
    Verwerkt taken en retourneert een geprioriteerde lijst met de 
    EERSTE incomplete subtaak per project.
    """
    grouped_tasks, parent_ids = group_parent_and_subtasks(raw_tasks)

    project_urgency = []

    for task in grouped_tasks:
        if task.get('subtasks'):
            # --- PROJECT MET SUB-TAKEN ---
            subtasks = task['subtasks']
            
            # Bereken TOTALE effort voor ALLE resterende sub-taken
            total_subtask_effort = sum(parse_effort(sub) for sub in subtasks)
            
            # Krijg de meest urgente deadline
            project_deadline = get_project_deadline(task, subtasks)
            
            # Bereken prioriteit gebaseerd op TOTAAL resterend werk
            priority, days_left, hours_per_day = calculate_priority(total_subtask_effort, project_deadline)
            
            # Neem alleen de EERSTE subtaak (ze zijn al gesorteerd)
            first_subtask = subtasks[0]
            
            project_urgency.append({
                'parent_task': task,
                'priority': priority,
                'days_until_deadline': days_left,
                'hours_per_day_needed': hours_per_day,
                'total_effort': total_subtask_effort,
                'first_subtask': first_subtask,
                'deadline_str': project_deadline.strftime("%Y-%m-%d") if project_deadline else "N/A",
                'deadline_dt': project_deadline,
                'all_subtasks': subtasks
            })
            
        else:
            # --- LOSSTAANDE TAAK ---
            effort = parse_effort(task)
            deadline = parse_deadline(task)
            priority, days_left, hours_per_day = calculate_priority(effort, deadline)
            
            project_urgency.append({
                'parent_task': task,
                'priority': priority,
                'days_until_deadline': days_left,
                'hours_per_day_needed': hours_per_day,
                'total_effort': effort,
                'first_subtask': None,
                'deadline_str': deadline.strftime("%Y-%m-%d") if deadline else "N/A",
                'deadline_dt': deadline
            })

    # Sorteer op urgentie (prioriteit, dan benodigde uren per dag)
    project_urgency.sort(key=lambda p: (
        PRIORITY_TIERS.index(p['priority']), 
        -p['hours_per_day_needed']
    ))

    # --- Bouw de definitieve takenlijst ---
    urgent_projects = []
    chore_projects = []
    
    # Sorteer projecten in T1-T5 (urgent) en T6-T7 (chores)
    for project in project_urgency:
        if project['priority'] in ['T1', 'T2', 'T3', 'T4', 'T5']:
            urgent_projects.append(project)
        else:  # T6, T7
            chore_projects.append(project)
    
    # Selecteer de top van elke lijst
    selected_projects = urgent_projects[:MAX_URGENT_TASKS] + chore_projects[:MAX_CHORE_TASKS]

    processed = []
    total_hours_selected = 0

    for project in selected_projects:
        if project['first_subtask']:
            # Project - gebruik de EERSTE subtaak
            first_sub = project['first_subtask']
            first_sub_effort = parse_effort(first_sub)
            processed.append({
                **first_sub,
                'effort_hours': first_sub_effort,
                'deadline_dt': project['deadline_dt'],
                'priority': project['priority'],
                'days_until_deadline': project['days_until_deadline'],
                'hours_per_day_needed': project['hours_per_day_needed'],
                'deadline_str': project['deadline_str'],
                'parent_title': project['parent_task'].get('title', 'Unknown'),
                'total_remaining_effort': project['total_effort'],
                'remaining_subtasks': len(project['all_subtasks']),
                'is_subtask': True
            })
            total_hours_selected += first_sub_effort
        else:
            # Losstaande taak
            effort = parse_effort(project['parent_task'])
            processed.append({
                **project['parent_task'],
                'effort_hours': effort,
                'deadline_dt': project['deadline_dt'],
                'priority': project['priority'],
                'days_until_deadline': project['days_until_deadline'],
                'hours_per_day_needed': project['hours_per_day_needed'],
                'deadline_str': project['deadline_str'],
                'parent_title': None,
                'total_remaining_effort': effort,
                'remaining_subtasks': 1,
                'is_subtask': False
            })
            total_hours_selected += effort

    return processed

#!/usr/bin/env python3
"""
Debug script to inspect actual Google Tasks data structure
Run this to see what fields are available and where deadlines are stored
"""

from auth import get_google_services
import json

def inspect_tasks():
    """Fetch and display raw task data to understand structure"""
    print("="*60)
    print("GOOGLE TASKS STRUCTURE INSPECTOR")
    print("="*60 + "\n")
    
    _, _, tasks_service = get_google_services()
    
    if not tasks_service:
        print("❌ Authentication failed")
        return
    
    # Get all task lists
    task_lists = tasks_service.tasklists().list().execute().get('items', [])
    
    print(f"Found {len(task_lists)} task lists\n")
    
    # Focus on Creative list since that's where your projects are
    for tlist in task_lists:
        if 'Creative' not in tlist['title']:
            continue
            
        print(f"\n{'='*60}")
        print(f"TASK LIST: {tlist['title']}")
        print(f"{'='*60}\n")
        
        # Get all tasks
        tasks = tasks_service.tasks().list(
            tasklist=tlist['id'],
            showCompleted=False,
            maxResults=500
        ).execute().get('items', [])
        
        # Find the parent tasks we care about
        target_parents = [
            'Schrijf De Aap is gaan staan',
            'Illustreer Hap. Slik. Weg.',
            'Website bouwen jeltesjoerd.com'
        ]
        
        for task in tasks:
            title = task.get('title', '')
            
            # Show parent tasks
            if title in target_parents:
                print(f"\n{'*'*60}")
                print(f"PARENT TASK: {title}")
                print(f"{'*'*60}")
                print(json.dumps(task, indent=2, default=str))
                print()
                
            # Show first subtask of each parent
            elif any(parent in str(task.get('notes', '')) for parent in target_parents):
                parent_id = task.get('parent')
                if parent_id:
                    # Find parent title
                    parent_task = next((t for t in tasks if t['id'] == parent_id), None)
                    if parent_task and parent_task.get('title') in target_parents:
                        print(f"\n{'-'*60}")
                        print(f"FIRST SUBTASK of '{parent_task.get('title')}':")
                        print(f"Title: {title}")
                        print(f"{'-'*60}")
                        print(json.dumps(task, indent=2, default=str))
                        print()
                        break  # Only show first one per parent

if __name__ == "__main__":
    inspect_tasks()

from src.models.tasks import task_from_dict

data = {
    'id': 'sub1',
    'title': 'Subtask',
    'parent': 'parent1'
}

task = task_from_dict(data)
print(f"Task parent_id: {task.parent_id}")

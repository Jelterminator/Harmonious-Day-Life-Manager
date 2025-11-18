# File: src/services/tasks_service.py

from typing import List, Dict, Any
from googleapiclient.discovery import Resource

from src.core.config_manager import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class GoogleTasksService:
    """Handles all Google Tasks operations."""
    
    def __init__(self, tasks_service: Resource):
        """
        Initialize tasks service.
        
        Args:
            tasks_service: Authenticated Google Tasks API resource
        """
        self.service = tasks_service
    
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """
        Fetch all open tasks from all task lists.
        
        NOTE: This method returns raw data (List[Dict]) and relies on DataCollector
        to convert it to the typed Task model.
        
        Returns:
            List of raw task dictionaries
        """
        logger.info("Fetching tasks from Google Tasks")
        
        all_tasks = []
        
        try:
            # 1. Get all task lists
            task_lists = self.service.tasklists().list().execute().get("items", [])
            logger.debug(f"Found {len(task_lists)} task lists")
            
            # 2. Iterate through each list and fetch tasks
            for tlist in task_lists:
                page_token = None
                
                while True:
                    kwargs = {
                        "tasklist": tlist["id"],
                        "showCompleted": False,
                        "maxResults": 100,
                    }
                    if page_token:
                        kwargs["pageToken"] = page_token
                        
                    response = self.service.tasks().list(**kwargs).execute()
                    
                    for task in response.get("items", []):
                        # Filter for non-completed tasks (status must be 'needsAction')
                        if task.get("status") != "needsAction":
                            continue
                            
                        # Map raw API response fields to the dictionary keys expected by task_from_dict
                        all_tasks.append({
                            "title": task.get("title", "No Title"),
                            "list_name": tlist["title"],  # Corresponds to list_name in Task model
                            "id": task["id"],
                            "parent_id": task.get("parent"), # Corresponds to parent_id in Task model
                            "deadline": task.get("due"),    # Corresponds to deadline in Task model
                            "notes": task.get("notes"),
                            "position": task.get("position", "0")
                        })
                        
                    page_token = response.get("nextPageToken")
                    if not page_token:
                        break
            
            logger.info(f"Fetched {len(all_tasks)} raw open tasks")
            return all_tasks
            
        except Exception as e:
            logger.error(f"Error fetching tasks from Google Tasks: {e}", exc_info=True)
            return []
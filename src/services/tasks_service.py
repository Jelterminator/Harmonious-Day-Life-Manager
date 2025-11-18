# File: src/services/tasks_service.py

import datetime
from typing import List, Dict, Any, Optional, Tuple
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
        
        Returns:
            List of task dictionaries
        """
        logger.info("Fetching tasks from Google Tasks")
        
        all_tasks = []
        
        try:
            task_lists = self.service.tasklists().list().execute().get("items", [])
            logger.debug(f"Found {len(task_lists)} task lists")
            
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
                        if task.get("status") != "needsAction":
                            continue
                        
                        all_tasks.append({
                            "title": task.get("title", "No Title"),
                            "list": tlist["title"],
                            "id": task["id"],
                            "parent": task.get("parent"),
                            "due": task.get("due"),
                            "notes": task.get("notes"),
                            "position": task.get("position", "0")
                        })
                    
                    page_token = response.get("nextPageToken")
                    if not page_token:
                        break
            
            logger.info(f"Fetched {len(all_tasks)} open tasks")
            return all_tasks
            
        except Exception as e:
            logger.error(f"Error fetching tasks: {e}", exc_info=True)
            return []
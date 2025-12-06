# File: tests/integration/test_orchestrator.py
"""
Integration tests for the Orchestrator pipeline.
Tests the full workflow with mocked external services.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.core.orchestrator import Orchestrator
from src.models.tasks import Task, PriorityTier
from src.models.habits import Habit, Frequency, habit_from_dict
from src.models.phase import Phase
from src.models.calendar import CalendarEvent
from src.models.schedule import Schedule, ScheduleEntry


@pytest.fixture
def mock_google_services():
    """Mock Google API services."""
    calendar = Mock()
    sheets = Mock()
    tasks = Mock()
    
    # Mock service responses
    calendar.events().list().execute.return_value = {'items': []}
    sheets.spreadsheets().values().get().execute.return_value = {'values': []}
    tasks.tasklists().list().execute.return_value = {'items': []}
    
    return calendar, sheets, tasks


@pytest.fixture
def sample_tasks():
    """Sample tasks for testing."""
    return [
        {
            'id': '1',
            'title': 'Urgent Task (2h)',
            'due': (datetime.now(timezone.utc) + timedelta(hours=20)).isoformat(),
            'status': 'needsAction',
            'parent': None,
            'notes': None,
            'effort_hours': 2.0
        },
        {
            'id': '2',
            'title': 'Normal Task (1h)',
            'due': (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
            'status': 'needsAction',
            'parent': None,
            'notes': None,
            'effort_hours': 1.0
        }
    ]


@pytest.fixture
def sample_habits():
    """Sample habits for testing."""
    return [
        ['id', 'title', 'duration_min', 'frequency', 'ideal_phase', 'task_type', 'due_day', 'active'],
        ['H01', 'Morning Meditation', '15', 'Daily', 'WOOD', 'spiritual', 'Every Day', 'Yes'],
        ['H02', 'Evening Reading', '30', 'Daily', 'WATER', 'learning', 'Every Day', 'Yes']
    ]


@pytest.fixture
def sample_calendar_events():
    """Sample calendar events for testing."""
    tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
    return [
        {
            'summary': 'Team Meeting',
            'start': {'dateTime': tomorrow.replace(hour=10).isoformat()},
            'end': {'dateTime': tomorrow.replace(hour=11).isoformat()},
            'extendedProperties': {'private': {}}
        }
    ]


class TestOrchestratorDataCollection:
    """Test Orchestrator data collection phase."""
    
    @patch('src.core.orchestrator.get_google_services')
    @patch('src.core.config_manager.Config.validate', return_value=True)
    @patch('src.core.config_manager.Config.load_phase_config')
    def test_data_collection_with_mock_services(
        self,
        mock_config,
        mock_validate,
        mock_auth,
        sample_tasks,
        sample_habits,
        sample_calendar_events
    ):
        """Test that orchestrator collects data from all services."""
        # Setup mocks
        mock_calendar = Mock()
        mock_sheets = Mock()
        mock_tasks = Mock()
        
        mock_calendar.events().list().execute.return_value = {
            'items': sample_calendar_events
        }
        
        mock_sheets.spreadsheets().values().get().execute.return_value = {
            'values': sample_habits
        }
        
        mock_tasks.tasklists().list().execute.return_value = {
            'items': [{'id': 'list1', 'title': 'My Tasks'}]
        }
        mock_tasks.tasks().list().execute.return_value = {
            'items': sample_tasks
        }
        
        mock_auth.return_value = (mock_calendar, mock_sheets, mock_tasks)
        mock_config.return_value = {
            'phases': [
                {'name': 'WOOD', 'start': '05:30', 'end': '09:00', 
                 'qualities': 'Growth', 'ideal_tasks': []}
            ],
            'anchors': []
        }
        
        # Create orchestrator
        orchestrator = Orchestrator()
        
        # Verify services were initialized
        assert orchestrator.calendar_service is not None
        assert orchestrator.sheets_service is not None
        assert orchestrator.tasks_service is not None


class TestOrchestratorTaskProcessing:
    """Test task processing in orchestrator."""
    
    def test_task_prioritization(self, sample_tasks):
        """Test that tasks are correctly prioritized."""
        from src.processors.task_processor import TaskProcessor
        
        processor = TaskProcessor()
        processed = processor.process_tasks(sample_tasks)
        
        # Urgent task should be first
        assert len(processed) > 0
        assert processed[0].priority in [PriorityTier.T1, PriorityTier.T2]
    
    def test_subtask_grouping(self):
        """Test that subtasks are grouped with parents."""
        from src.processors.task_processor import TaskProcessor
        
        tasks = [
            {
                'id': 'parent1',
                'title': 'Parent Task',
                'due': (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
                'status': 'needsAction',
                'parent': None,
                'effort_hours': 4.0
            },
            {
                'id': 'sub1',
                'title': '01. First Subtask (1h)',
                'due': None,
                'status': 'needsAction',
                'parent': 'parent1',
                'position': '1'
            },
            {
                'id': 'sub2',
                'title': '02. Second Subtask (1h)',
                'due': None,
                'status': 'needsAction',
                'parent': 'parent1',
                'position': '2'
            }
        ]
        
        processor = TaskProcessor()
        processed = processor.process_tasks(tasks)
        
        # Should have subtasks in correct order
        subtasks = [t for t in processed if getattr(t, 'is_subtask', False)]
        assert len(subtasks) >= 2


class TestOrchestratorHabitProcessing:
    """Test habit processing in orchestrator."""
    
    def test_daily_habit_filtering(self, sample_habits):
        """Test that daily habits are included."""
        from src.processors.habit_processor import filter_habits
        
        # Convert sample data to Habit objects
        headers = sample_habits[0]
        habits = []
        for row in sample_habits[1:]:
            data = {headers[i]: row[i] for i in range(len(headers))}
            habits.append(habit_from_dict(data))
        
        filtered = filter_habits(habits)
        
        # Should include both daily habits
        assert len(filtered) >= 2
    
    def test_weekly_habit_filtering(self):
        """Test that weekly habits are filtered correctly."""
        from src.processors.habit_processor import filter_habits
        import datetime
        
        today = datetime.date.today().strftime("%A")
        
        habits_data = [
            {
                'title': 'Weekly Habit',
                'active': 'Yes',
                'frequency': 'Weekly',
                'due_day': today
            },
            {
                'title': 'Other Day Habit',
                'active': 'Yes',
                'frequency': 'Weekly',
                'due_day': 'Monday' if today != 'Monday' else 'Tuesday'
            }
        ]
        
        habits = [habit_from_dict(h) for h in habits_data]
        
        filtered = filter_habits(habits)
        
        # Should only include today's habit
        assert len(filtered) == 1
        assert filtered[0].title == 'Weekly Habit'


class TestOrchestratorConflictDetection:
    """Test conflict detection between entries and calendar events."""
    
    def test_overlap_detection(self):
        """Test that overlapping entries are detected."""
        from src.processors.schedule_processor import ScheduleProcessor
        
        processor = ScheduleProcessor()
        
        entries = [
            ScheduleEntry(
                title='Task',
                start_time=datetime(2025, 11, 18, 10, 0),
                end_time=datetime(2025, 11, 18, 11, 0),
                phase=Phase.FIRE,
                date_indicator='today'
            )
        ]
        
        events = [
            CalendarEvent(
                summary='Meeting',
                start=datetime(2025, 11, 18, 10, 30),
                end=datetime(2025, 11, 18, 11, 30)
            )
        ]
        
        filtered = processor.filter_conflicting_entries(entries, events)
        
        # Task should be filtered due to conflict
        assert len(filtered) == 0
    
    def test_no_overlap_preserved(self):
        """Test that non-overlapping entries are preserved."""
        from src.processors.schedule_processor import ScheduleProcessor
        
        processor = ScheduleProcessor()
        
        entries = [
            ScheduleEntry(
                title='Task',
                start_time=datetime(2025, 11, 18, 9, 0),
                end_time=datetime(2025, 11, 18, 10, 0),
                phase=Phase.FIRE,
                date_indicator='today'
            )
        ]
        
        events = [
            CalendarEvent(
                summary='Meeting',
                start=datetime(2025, 11, 18, 11, 0),
                end=datetime(2025, 11, 18, 12, 0)
            )
        ]
        
        filtered = processor.filter_conflicting_entries(entries, events)
        
        # Task should be preserved (no conflict)
        assert len(filtered) == 1


class TestOrchestratorPromptBuilding:
    """Test prompt building for LLM."""
    
    def test_prompt_includes_all_constraints(self):
        """Test that prompt includes all necessary information."""
        from src.llm.prompt_builder import PromptBuilder
        
        rules = {
            'phases': [
                {
                    'name': 'WOOD',
                    'start': '05:30',
                    'end': '09:00',
                    'qualities': 'Growth',
                    'ideal_tasks': []
                }
            ],
            'anchors': [
                {'name': 'Fajr', 'time': '05:30-05:40', 'phase': 'WOOD'}
            ]
        }
        
        builder = PromptBuilder(rules)
        
        prompt = builder.build_world_prompt(
            calendar_events=[],
            tasks=[],
            habits=[]
        )
        
        # Check key sections
        assert "SCHEDULE REQUEST" in prompt
        assert "AVAILABLE PHASE WINDOWS:" in prompt
        assert "STONES:" in prompt
        assert "PEBBLES:" in prompt
        assert "SAND:" in prompt


class TestEndToEndPipeline:
    """Test complete end-to-end pipeline (mocked)."""
    
    @patch('src.core.orchestrator.get_google_services')
    @patch('src.core.orchestrator.load_system_prompt')
    @patch('src.core.orchestrator.call_groq_llm')
    @patch('src.core.config_manager.Config.validate', return_value=True)
    @patch('src.core.config_manager.Config.load_phase_config')
    def test_full_pipeline_mock(
        self,
        mock_config,
        mock_validate,
        mock_llm,
        mock_load_prompt,
        mock_auth,
        sample_tasks,
        sample_habits,
        sample_calendar_events
    ):
        """Test complete pipeline with all components mocked."""
        # Setup config
        mock_config.return_value = {
            'phases': [
                {
                    'name': 'WOOD',
                    'start': '05:30',
                    'end': '09:00',
                    'qualities': 'Growth',
                    'ideal_tasks': []
                }
            ],
            'anchors': []
        }
        
        # Setup mock system prompt
        mock_load_prompt.return_value = "System Prompt Content"
        
        # Setup services
        mock_calendar = Mock()
        mock_sheets = Mock()
        mock_tasks_service = Mock()
        
        mock_calendar.events().list().execute.return_value = {
            'items': sample_calendar_events
        }
        mock_sheets.spreadsheets().values().get().execute.return_value = {
            'values': sample_habits
        }
        mock_tasks_service.tasklists().list().execute.return_value = {
            'items': [{'id': 'list1', 'title': 'Tasks'}]
        }
        mock_tasks_service.tasks().list().execute.return_value = {
            'items': sample_tasks
        }
        
        mock_auth.return_value = (mock_calendar, mock_sheets, mock_tasks_service)
        
        # Setup LLM response
        today = datetime.now(timezone.utc)
        start_time = today.replace(hour=9, minute=0, second=0, microsecond=0)
        end_time = today.replace(hour=10, minute=0, second=0, microsecond=0)
        
        mock_llm.return_value = {
            'status': 'success',
            'output': [
                ScheduleEntry(
                    title='Generated Task',
                    start_time=start_time,
                    end_time=end_time,
                    phase=Phase.FIRE,
                    date_indicator='today'
                )
            ]
        }
        
        # Run orchestrator
        orchestrator = Orchestrator()
        result = orchestrator.run_daily_plan()
        
        # Verify success
        assert result is True
        
        # Verify LLM was called
        assert mock_llm.called
        
        # Verify calendar service was used to create events
        # (Would need additional mocking for calendar.create_events)
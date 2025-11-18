# File: tests/conftest.py
"""
Pytest configuration and shared fixtures.
Provides reusable test data and mocks for all tests.
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, MagicMock
import sys

# Add src to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.models.models import (
    Task, PriorityTier, Habit, Frequency, Phase,
    CalendarEvent, ScheduleEntry, Schedule
)


# ==================== Configuration Fixtures ====================

@pytest.fixture
def sample_config():
    """Sample application configuration."""
    return {
        'phases': [
            {
                'name': 'WOOD',
                'start': '05:30',
                'end': '09:00',
                'qualities': 'Growth, Planning, Vitality',
                'ideal_tasks': ['spiritual', 'planning', 'movement']
            },
            {
                'name': 'FIRE',
                'start': '09:00',
                'end': '13:00',
                'qualities': 'Peak energy, expression',
                'ideal_tasks': ['deep_work', 'creative']
            },
            {
                'name': 'EARTH',
                'start': '13:00',
                'end': '15:00',
                'qualities': 'Stability, nourishment',
                'ideal_tasks': ['rest', 'integration']
            },
            {
                'name': 'METAL',
                'start': '15:00',
                'end': '18:00',
                'qualities': 'Precision, organization',
                'ideal_tasks': ['admin', 'planning']
            },
            {
                'name': 'WATER',
                'start': '18:00',
                'end': '21:45',
                'qualities': 'Rest, consolidation',
                'ideal_tasks': ['rest', 'reflection']
            }
        ],
        'anchors': [
            {'name': 'Fajr', 'time': '05:30-05:40', 'phase': 'WOOD'},
            {'name': 'Zuhr', 'time': '13:00-13:20', 'phase': 'EARTH'},
            {'name': 'Asr', 'time': '15:00-15:20', 'phase': 'METAL'},
            {'name': 'Maghrib', 'time': '18:00-18:15', 'phase': 'WATER'},
            {'name': 'Isha', 'time': '21:00-21:20', 'phase': 'WATER'}
        ]
    }


# ==================== Task Fixtures ====================

@pytest.fixture
def urgent_task():
    """Create an urgent task (T1)."""
    deadline = datetime.now() + timedelta(days=1)
    return Task(
        id="urgent_1",
        title="Urgent Task",
        effort_hours=8.0,
        priority=PriorityTier.T1,
        deadline=deadline,
        days_until_deadline=1.0,
        hours_per_day_needed=8.0
    )


@pytest.fixture
def normal_task():
    """Create a normal task (T4)."""
    deadline = datetime.now() + timedelta(days=7)
    return Task(
        id="normal_1",
        title="Normal Task",
        effort_hours=2.0,
        priority=PriorityTier.T4,
        deadline=deadline,
        days_until_deadline=7.0,
        hours_per_day_needed=0.3
    )


@pytest.fixture
def task_with_subtasks():
    """Create a parent task with subtasks."""
    parent = Task(
        id="parent_1",
        title="Parent Task",
        effort_hours=0.0,
        priority=PriorityTier.T2,
        deadline=datetime.now() + timedelta(days=3)
    )
    
    subtask1 = Task(
        id="sub_1",
        title="01. First Subtask",
        effort_hours=2.0,
        priority=PriorityTier.T2,
        parent_id="parent_1",
        parent_title="Parent Task",
        is_subtask=True
    )
    
    subtask2 = Task(
        id="sub_2",
        title="02. Second Subtask",
        effort_hours=3.0,
        priority=PriorityTier.T2,
        parent_id="parent_1",
        parent_title="Parent Task",
        is_subtask=True
    )
    
    return parent, [subtask1, subtask2]


@pytest.fixture
def sample_tasks(urgent_task, normal_task):
    """Collection of sample tasks."""
    return [urgent_task, normal_task]


# ==================== Habit Fixtures ====================

@pytest.fixture
def daily_habit():
    """Create a daily habit."""
    return Habit(
        id="H01",
        title="Morning Meditation",
        duration_min=15,
        frequency=Frequency.DAILY,
        ideal_phase=Phase.WOOD,
        task_type="spiritual",
        active=True
    )


@pytest.fixture
def weekly_habit():
    """Create a weekly habit."""
    return Habit(
        id="H02",
        title="Weekly Review",
        duration_min=30,
        frequency=Frequency.WEEKLY,
        ideal_phase=Phase.METAL,
        task_type="reflection",
        due_day="Sunday",
        active=True
    )


@pytest.fixture
def sample_habits(daily_habit, weekly_habit):
    """Collection of sample habits."""
    return [daily_habit, weekly_habit]


# ==================== Calendar Event Fixtures ====================

@pytest.fixture
def calendar_event():
    """Create a calendar event."""
    start = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=1)
    
    return CalendarEvent(
        summary="Team Meeting",
        start=start,
        end=end,
        event_id="event_1"
    )


@pytest.fixture
def sample_calendar_events(calendar_event):
    """Collection of sample calendar events."""
    return [calendar_event]


# ==================== Schedule Fixtures ====================

@pytest.fixture
def schedule_entry():
    """Create a schedule entry."""
    start = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=2)
    
    return ScheduleEntry(
        title="Deep Work Session",
        start_time=start,
        end_time=end,
        phase=Phase.FIRE,
        date_indicator="today"
    )


@pytest.fixture
def sample_schedule(schedule_entry):
    """Create a sample schedule."""
    schedule = Schedule()
    schedule.add_entry(schedule_entry)
    return schedule


# ==================== Mock Service Fixtures ====================

@pytest.fixture
def mock_calendar_service():
    """Mock Google Calendar service."""
    mock = Mock()
    mock.events().list().execute.return_value = {'items': []}
    mock.events().insert().execute.return_value = {'id': 'new_event_id'}
    mock.events().delete().execute.return_value = None
    return mock


@pytest.fixture
def mock_sheets_service():
    """Mock Google Sheets service."""
    mock = Mock()
    mock.spreadsheets().values().get().execute.return_value = {
        'values': [
            ['id', 'title', 'duration_min', 'frequency', 'ideal_phase', 'task_type', 'due_day', 'active'],
            ['H01', 'Test Habit', '15', 'Daily', 'WOOD', 'spiritual', 'Every Day', 'Yes']
        ]
    }
    return mock


@pytest.fixture
def mock_tasks_service():
    """Mock Google Tasks service."""
    mock = Mock()
    mock.tasklists().list().execute.return_value = {
        'items': [{'id': 'list1', 'title': 'My Tasks'}]
    }
    mock.tasks().list().execute.return_value = {
        'items': [
            {
                'id': 'task1',
                'title': 'Test Task (2h)',
                'status': 'needsAction',
                'due': (datetime.now() + timedelta(days=3)).isoformat()
            }
        ]
    }
    return mock


@pytest.fixture
def mock_google_services(mock_calendar_service, mock_sheets_service, mock_tasks_service):
    """Mock all Google services together."""
    return mock_calendar_service, mock_sheets_service, mock_tasks_service


# ==================== LLM Mock Fixtures ====================

@pytest.fixture
def mock_llm_success_response():
    """Mock successful LLM response."""
    return {
        'status': 'success',
        'output': {
            'schedule_entries': [
                {
                    'title': 'Generated Task',
                    'start_time': '2025-11-18T09:00:00',
                    'end_time': '2025-11-18T10:00:00',
                    'phase': 'FIRE',
                    'date': 'today'
                }
            ]
        },
        'raw': {}
    }


@pytest.fixture
def mock_llm_failure_response():
    """Mock failed LLM response."""
    return {
        'status': 'fail',
        'message': 'API error: Connection timeout',
        'raw': None
    }


# ==================== Temporary Directory Fixtures ====================

@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary config directory."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    
    # Create sample config.json
    config_file = config_dir / "config.json"
    config_file.write_text('{"phases": [], "anchors": []}')
    
    # Create sample system_prompt.txt
    prompt_file = config_dir / "system_prompt.txt"
    prompt_file.write_text("You are a scheduling assistant.")
    
    return config_dir


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create temporary output directory."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def temp_logs_dir(tmp_path):
    """Create temporary logs directory."""
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    return logs_dir


# ==================== Date/Time Fixtures ====================

@pytest.fixture
def today():
    """Get today's date."""
    return datetime.now().date()


@pytest.fixture
def tomorrow():
    """Get tomorrow's date."""
    return (datetime.now() + timedelta(days=1)).date()


@pytest.fixture
def next_week():
    """Get date one week from now."""
    return (datetime.now() + timedelta(days=7)).date()


# ==================== Pytest Markers ====================

def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "external: mark test as requiring external services"
    )


# ==================== Auto-use Fixtures ====================

@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset any singleton instances between tests."""
    # Add singleton reset logic here if needed
    yield
    # Cleanup after test


@pytest.fixture(autouse=True)
def isolate_environment(monkeypatch):
    """Isolate environment variables for each test."""
    # This ensures tests don't interfere with each other
    yield


# ==================== Helper Functions ====================

@pytest.fixture
def assert_schedule_valid():
    """Helper function to validate schedules."""
    def _assert_valid(schedule: Schedule):
        """Assert that a schedule is valid."""
        assert len(schedule.entries) > 0, "Schedule should have entries"
        assert not schedule.has_conflicts(), "Schedule should have no conflicts"
        
        for entry in schedule.entries:
            assert entry.title, "Entry should have title"
            assert entry.start_time < entry.end_time, "Start should be before end"
            assert entry.phase in Phase, "Entry should have valid phase"
    
    return _assert_valid


@pytest.fixture
def create_test_task():
    """Factory fixture for creating test tasks."""
    def _create(
        title: str = "Test Task",
        priority: PriorityTier = PriorityTier.T4,
        effort_hours: float = 1.0,
        deadline_days: int = 7
    ) -> Task:
        """Create a test task with given parameters."""
        return Task(
            id=f"test_{title.lower().replace(' ', '_')}",
            title=title,
            effort_hours=effort_hours,
            priority=priority,
            deadline=datetime.now() + timedelta(days=deadline_days)
        )
    
    return _create


@pytest.fixture
def create_test_habit():
    """Factory fixture for creating test habits."""
    def _create(
        title: str = "Test Habit",
        duration_min: int = 15,
        frequency: Frequency = Frequency.DAILY,
        phase: Phase = Phase.WOOD
    ) -> Habit:
        """Create a test habit with given parameters."""
        return Habit(
            id=f"test_{title.lower().replace(' ', '_')}",
            title=title,
            duration_min=duration_min,
            frequency=frequency,
            ideal_phase=phase,
            task_type="test",
            active=True
        )
    
    return _create
# File: tests/unit/test_models.py
"""
Unit tests for data models.
Tests all dataclasses and their methods.
"""

import pytest
from datetime import datetime, timedelta
from src.models.tasks import Task, task_from_dict
from src.models.enums import PriorityTier, Frequency
from src.models.phase import Phase
from src.models.habits import Habit, habit_from_dict
from src.models.calendar import CalendarEvent
from src.models.schedule import ScheduleEntry, Schedule


# ==================== Task Tests ====================

class TestTask:
    """Tests for Task dataclass."""
    
    def test_task_creation(self):
        """Test basic task creation."""
        task = Task(
            id="1",
            title="Test Task",
            effort_hours=2.0,
            priority=PriorityTier.T2
        )
        
        assert task.id == "1"
        assert task.title == "Test Task"
        assert task.effort_hours == 2.0
        assert task.priority == PriorityTier.T2
    
    def test_task_with_deadline(self):
        """Test task with deadline."""
        deadline = datetime.now() + timedelta(days=3)
        task = Task(
            id="1",
            title="Urgent Task",
            effort_hours=8.0,
            priority=PriorityTier.T1,
            deadline=deadline
        )
        
        assert task.deadline == deadline
        assert task.deadline_str == deadline.strftime("%Y-%m-%d")
    
    def test_task_is_urgent(self):
        """Test urgency detection."""
        urgent_task = Task("1", "Urgent", 2.0, PriorityTier.T1)
        normal_task = Task("2", "Normal", 2.0, PriorityTier.T4)
        
        assert urgent_task.is_urgent() is True
        assert normal_task.is_urgent() is False
    
    def test_task_is_overdue(self):
        """Test overdue detection."""
        past = datetime.now() - timedelta(days=1)
        future = datetime.now() + timedelta(days=1)
        
        overdue_task = Task("1", "Overdue", 1.0, PriorityTier.T1, deadline=past)
        future_task = Task("2", "Future", 1.0, PriorityTier.T1, deadline=future)
        no_deadline = Task("3", "No Deadline", 1.0, PriorityTier.T1)
        
        assert overdue_task.is_overdue() is True
        assert future_task.is_overdue() is False
        assert no_deadline.is_overdue() is False
    
    def test_task_negative_effort_raises_error(self):
        """Test that negative effort raises ValueError."""
        with pytest.raises(ValueError, match="cannot be negative"):
            Task("1", "Bad Task", -2.0, PriorityTier.T1)
    
    def test_task_to_dict(self):
        """Test conversion to dictionary."""
        task = Task(
            id="1",
            title="Test",
            effort_hours=2.0,
            priority=PriorityTier.T2,
            is_subtask=True
        )
        
        result = task.to_dict()
        
        assert result['id'] == "1"
        assert result['title'] == "Test"
        assert result['effort_hours'] == 2.0
        assert result['priority'] == "T2"
        assert result['is_subtask'] is True
    
    def test_task_from_dict(self):
        """Test creating task from dictionary."""
        data = {
            'id': '1',
            'title': 'Test Task',
            'effort_hours': 3.0,
            'priority': 'T3',
            'is_subtask': False
        }
        
        task = task_from_dict(data)
        
        assert task.id == "1"
        assert task.title == "Test Task"
        assert task.effort_hours == 3.0
        assert task.priority == PriorityTier.T3


# ==================== Habit Tests ====================

class TestHabit:
    """Tests for Habit dataclass."""
    
    def test_habit_creation(self):
        """Test basic habit creation."""
        habit = Habit(
            id="H01",
            title="Morning Meditation",
            duration_min=15,
            frequency=Frequency.DAILY,
            ideal_phase=Phase.WOOD,
            task_type="spiritual"
        )
        
        assert habit.id == "H01"
        assert habit.title == "Morning Meditation"
        assert habit.duration_min == 15
        assert habit.frequency == Frequency.DAILY
        assert habit.ideal_phase == Phase.WOOD
    
    def test_habit_is_scheduled_today_daily(self):
        """Test daily habit scheduling."""
        habit = Habit(
            "H01", "Daily Habit", 15,
            Frequency.DAILY, Phase.WOOD, "spiritual"
        )
        
        assert habit.is_scheduled_today("Monday") is True
        assert habit.is_scheduled_today("Sunday") is True
    
    def test_habit_is_scheduled_today_weekly(self):
        """Test weekly habit scheduling."""
        habit = Habit(
            "H01", "Weekly Habit", 30,
            Frequency.WEEKLY, Phase.METAL, "reflection",
            due_day="Sunday"
        )
        
        assert habit.is_scheduled_today("Sunday") is True
        assert habit.is_scheduled_today("Monday") is False
        assert habit.is_scheduled_today("sunday") is True  # Case insensitive
    
    def test_habit_inactive_not_scheduled(self):
        """Test inactive habits are not scheduled."""
        habit = Habit(
            "H01", "Inactive", 15,
            Frequency.DAILY, Phase.WOOD, "spiritual",
            active=False
        )
        
        assert habit.is_scheduled_today("Monday") is False
    
    def test_habit_invalid_duration_raises_error(self):
        """Test that invalid duration raises ValueError."""
        with pytest.raises(ValueError, match="Duration must be positive"):
            Habit("H01", "Bad Habit", -10, Frequency.DAILY, Phase.WOOD, "spiritual")
    
    def test_habit_to_dict(self):
        """Test conversion to dictionary."""
        habit = Habit(
            "H01", "Test Habit", 20,
            Frequency.WEEKLY, Phase.FIRE, "exercise",
            due_day="Wednesday", active=True
        )
        
        result = habit.to_dict()
        
        assert result['id'] == "H01"
        assert result['title'] == "Test Habit"
        assert result['duration_min'] == 20
        assert result['frequency'] == "Weekly"
        assert result['ideal_phase'] == "FIRE"


# ==================== CalendarEvent Tests ====================

class TestCalendarEvent:
    """Tests for CalendarEvent dataclass."""
    
    def test_event_creation(self):
        """Test basic event creation."""
        start = datetime(2025, 11, 18, 10, 0)
        end = datetime(2025, 11, 18, 11, 0)
        
        event = CalendarEvent(
            summary="Meeting",
            start=start,
            end=end
        )
        
        assert event.summary == "Meeting"
        assert event.start == start
        assert event.end == end
    
    def test_event_duration_minutes(self):
        """Test duration calculation."""
        start = datetime(2025, 11, 18, 10, 0)
        end = datetime(2025, 11, 18, 11, 30)
        
        event = CalendarEvent("Meeting", start, end)
        
        assert event.duration_minutes() == 90
    
    def test_event_invalid_times_raises_error(self):
        """Test that end before start raises ValueError."""
        start = datetime(2025, 11, 18, 11, 0)
        end = datetime(2025, 11, 18, 10, 0)
        
        with pytest.raises(ValueError, match="end time must be after start"):
            CalendarEvent("Bad Event", start, end)
    
    def test_event_overlaps_with(self):
        """Test overlap detection."""
        event1 = CalendarEvent(
            "Event 1",
            datetime(2025, 11, 18, 10, 0),
            datetime(2025, 11, 18, 11, 0)
        )
        
        # Overlapping event
        event2 = CalendarEvent(
            "Event 2",
            datetime(2025, 11, 18, 10, 30),
            datetime(2025, 11, 18, 11, 30)
        )
        
        # Non-overlapping event
        event3 = CalendarEvent(
            "Event 3",
            datetime(2025, 11, 18, 11, 0),
            datetime(2025, 11, 18, 12, 0)
        )
        
        assert event1.overlaps_with(event2) is True
        assert event1.overlaps_with(event3) is False


# ==================== ScheduleEntry Tests ====================

class TestScheduleEntry:
    """Tests for ScheduleEntry dataclass."""
    
    def test_entry_creation(self):
        """Test basic entry creation."""
        start = datetime(2025, 11, 18, 9, 0)
        end = datetime(2025, 11, 18, 10, 0)
        
        entry = ScheduleEntry(
            title="Deep Work",
            start_time=start,
            end_time=end,
            phase=Phase.FIRE,
            date_indicator="today"
        )
        
        assert entry.title == "Deep Work"
        assert entry.phase == Phase.FIRE
        assert entry.date_indicator == "today"
    
    def test_entry_duration_minutes(self):
        """Test duration calculation."""
        entry = ScheduleEntry(
            "Task",
            datetime(2025, 11, 18, 9, 0),
            datetime(2025, 11, 18, 11, 30),
            Phase.FIRE,
            "today"
        )
        
        assert entry.duration_minutes() == 150
    
    def test_entry_overlaps_with(self):
        """Test overlap detection between entries."""
        entry1 = ScheduleEntry(
            "Task 1",
            datetime(2025, 11, 18, 9, 0),
            datetime(2025, 11, 18, 10, 0),
            Phase.FIRE,
            "today"
        )
        
        entry2 = ScheduleEntry(
            "Task 2",
            datetime(2025, 11, 18, 9, 30),
            datetime(2025, 11, 18, 10, 30),
            Phase.FIRE,
            "today"
        )
        
        entry3 = ScheduleEntry(
            "Task 3",
            datetime(2025, 11, 18, 10, 0),
            datetime(2025, 11, 18, 11, 0),
            Phase.FIRE,
            "today"
        )
        
        assert entry1.overlaps_with(entry2) is True
        assert entry1.overlaps_with(entry3) is False
    
    def test_entry_to_dict(self):
        """Test conversion to dictionary."""
        entry = ScheduleEntry(
            "Test Task",
            datetime(2025, 11, 18, 9, 0),
            datetime(2025, 11, 18, 10, 0),
            Phase.FIRE,
            "today"
        )
        
        result = entry.to_dict()
        
        assert result['title'] == "Test Task"
        assert result['phase'] == "FIRE"
        assert result['date'] == "today"
        assert 'start_time' in result
        assert 'end_time' in result


# ==================== Schedule Tests ====================

class TestSchedule:
    """Tests for Schedule dataclass."""
    
    def test_schedule_creation(self):
        """Test basic schedule creation."""
        schedule = Schedule()
        
        assert len(schedule.entries) == 0
        assert isinstance(schedule.generation_date, datetime)
    
    def test_schedule_add_entry(self):
        """Test adding entries to schedule."""
        schedule = Schedule()
        
        entry = ScheduleEntry(
            "Task",
            datetime(2025, 11, 18, 9, 0),
            datetime(2025, 11, 18, 10, 0),
            Phase.FIRE,
            "today"
        )
        
        schedule.add_entry(entry)
        
        assert len(schedule.entries) == 1
        assert schedule.entries[0] == entry
    
    def test_schedule_get_entries_by_phase(self):
        """Test filtering entries by phase."""
        schedule = Schedule()
        
        fire_entry = ScheduleEntry(
            "Fire Task",
            datetime(2025, 11, 18, 9, 0),
            datetime(2025, 11, 18, 10, 0),
            Phase.FIRE,
            "today"
        )
        
        wood_entry = ScheduleEntry(
            "Wood Task",
            datetime(2025, 11, 18, 6, 0),
            datetime(2025, 11, 18, 7, 0),
            Phase.WOOD,
            "today"
        )
        
        schedule.add_entry(fire_entry)
        schedule.add_entry(wood_entry)
        
        fire_entries = schedule.get_entries_by_phase(Phase.FIRE)
        
        assert len(fire_entries) == 1
        assert fire_entries[0].title == "Fire Task"
    
    def test_schedule_get_entries_for_date(self):
        """Test filtering entries by date."""
        schedule = Schedule()
        
        today_entry = ScheduleEntry(
            "Today",
            datetime(2025, 11, 18, 9, 0),
            datetime(2025, 11, 18, 10, 0),
            Phase.FIRE,
            "today"
        )
        
        tomorrow_entry = ScheduleEntry(
            "Tomorrow",
            datetime(2025, 11, 19, 9, 0),
            datetime(2025, 11, 19, 10, 0),
            Phase.FIRE,
            "tomorrow"
        )
        
        schedule.add_entry(today_entry)
        schedule.add_entry(tomorrow_entry)
        
        today_entries = schedule.get_entries_for_date("today")
        
        assert len(today_entries) == 1
        assert today_entries[0].title == "Today"
    
    def test_schedule_total_scheduled_minutes(self):
        """Test calculating total scheduled time."""
        schedule = Schedule()
        
        # 1 hour entry
        schedule.add_entry(ScheduleEntry(
            "Task 1",
            datetime(2025, 11, 18, 9, 0),
            datetime(2025, 11, 18, 10, 0),
            Phase.FIRE,
            "today"
        ))
        
        # 30 minute entry
        schedule.add_entry(ScheduleEntry(
            "Task 2",
            datetime(2025, 11, 18, 10, 0),
            datetime(2025, 11, 18, 10, 30),
            Phase.FIRE,
            "today"
        ))
        
        assert schedule.total_scheduled_minutes() == 90
    
    def test_schedule_has_conflicts(self):
        """Test conflict detection."""
        schedule = Schedule()
        
        # Overlapping entries
        schedule.add_entry(ScheduleEntry(
            "Task 1",
            datetime(2025, 11, 18, 9, 0),
            datetime(2025, 11, 18, 10, 0),
            Phase.FIRE,
            "today"
        ))
        
        schedule.add_entry(ScheduleEntry(
            "Task 2",
            datetime(2025, 11, 18, 9, 30),
            datetime(2025, 11, 18, 10, 30),
            Phase.FIRE,
            "today"
        ))
        
        assert schedule.has_conflicts() is True
    
    def test_schedule_no_conflicts(self):
        """Test schedule without conflicts."""
        schedule = Schedule()
        
        # Non-overlapping entries
        schedule.add_entry(ScheduleEntry(
            "Task 1",
            datetime(2025, 11, 18, 9, 0),
            datetime(2025, 11, 18, 10, 0),
            Phase.FIRE,
            "today"
        ))
        
        schedule.add_entry(ScheduleEntry(
            "Task 2",
            datetime(2025, 11, 18, 10, 0),
            datetime(2025, 11, 18, 11, 0),
            Phase.FIRE,
            "today"
        ))
        
        assert schedule.has_conflicts() is False


# ==================== Enum Tests ====================

class TestEnums:
    """Tests for enum types."""
    
    def test_priority_tier_values(self):
        """Test PriorityTier enum values."""
        assert PriorityTier.T1.value == "T1"
        assert PriorityTier.T6.value == "T6"
    
    def test_phase_values(self):
        """Test Phase enum values."""
        assert Phase.WOOD.value == "WOOD"
        assert Phase.FIRE.value == "FIRE"
        assert Phase.WATER.value == "WATER"
    
    def test_frequency_values(self):
        """Test Frequency enum values."""
        assert Frequency.DAILY.value == "Daily"
        assert Frequency.WEEKLY.value == "Weekly"


# ==================== Integration Tests ====================

class TestModelIntegration:
    """Integration tests combining multiple models."""
    
    def test_task_to_schedule_entry_workflow(self):
        """Test converting task to schedule entry."""
        task = Task(
            "1",
            "Important Task",
            2.0,
            PriorityTier.T2,
            deadline=datetime(2025, 11, 20)
        )
        
        entry = ScheduleEntry(
            title=task.title,
            start_time=datetime(2025, 11, 18, 9, 0),
            end_time=datetime(2025, 11, 18, 11, 0),
            phase=Phase.FIRE,
            date_indicator="today",
            task_id=task.id
        )
        
        assert entry.title == task.title
        assert entry.task_id == task.id
        assert entry.duration_minutes() == 120  # 2 hours
    
    def test_habit_to_schedule_entry_workflow(self):
        """Test converting habit to schedule entry."""
        habit = Habit(
            "H01",
            "Morning Meditation",
            15,
            Frequency.DAILY,
            Phase.WOOD,
            "spiritual"
        )
        
        entry = ScheduleEntry(
            title=habit.title,
            start_time=datetime(2025, 11, 18, 6, 0),
            end_time=datetime(2025, 11, 18, 6, 15),
            phase=habit.ideal_phase,
            date_indicator="today",
            habit_id=habit.id
        )
        
        assert entry.title == habit.title
        assert entry.phase == habit.ideal_phase
        assert entry.duration_minutes() == habit.duration_min
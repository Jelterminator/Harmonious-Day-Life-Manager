import unittest
import datetime
import pytz
from unittest.mock import MagicMock

# ---- IMPORT YOUR ORCHESTRATOR CLASS ----
from main import Orchestrator

TARGET_TIMEZONE = "Europe/Amsterdam"
local_tz = pytz.timezone(TARGET_TIMEZONE)


# ----------------------
# Fake Google Calendar
# ----------------------
class FakeGoogleCalendarService:
    def new_batch_http_request(self):
        return FakeBatchRequest()

    class events:
        @staticmethod
        def insert(calendarId, body):
            return f"EVENT_INSERT:{body['summary']}"


class FakeBatchRequest:
    def __init__(self):
        self._requests = []

    def add(self, request, callback):
        self._requests.append((request, callback))

    def execute(self):
        # Simulate all inserts succeeding
        for req, cb in self._requests:
            cb("req_id", {"status": "ok"}, None)


# ----------------------
# Test Suite
# ----------------------
class TestOrchestrator(unittest.TestCase):

    def setUp(self):
        """
        Build a minimal Orchestrator instance.
        We bypass authentication and inject our fake calendar service.
        """
        self.o = Orchestrator.__new__(Orchestrator)  # Do NOT call __init__

        # Required attributes normally set in __init__
        self.o.services = {"calendar": FakeGoogleCalendarService()}
        self.o.today_date_str = "2025-11-17"

        # Inject constants that the class normally has
        global TARGET_TIMEZONE
        TARGET_TIMEZONE = "Europe/Paris"

    # --------------------
    # parse_iso_to_local
    # --------------------
    def test_parse_time_only(self):
        dt = self.o.parse_iso_to_local("08:00", datetime.date(2025, 10, 10))
        self.assertEqual(dt.hour, 8)
        self.assertEqual(dt.minute, 0)
        self.assertEqual(dt.tzinfo.zone, local_tz.zone)

    def test_parse_iso_z(self):
        dt = self.o.parse_iso_to_local("2025-11-17T05:00:00Z")
        self.assertEqual(dt.tzinfo.zone, local_tz.zone)

    def test_parse_full_iso(self):
        dt = self.o.parse_iso_to_local("2025-11-17T09:30:00+02:00")
        self.assertEqual(dt.astimezone(local_tz).hour, 8)

    # --------------------
    # Conflict Handling
    # --------------------
    def test_conflict(self):
        fixed_events = [
            {
                "summary": "Meeting",
                "start": "2025-11-17T09:00:00+01:00",
                "end":   "2025-11-17T10:00:00+01:00",
            }
        ]
        schedule = [
            {
                "title": "Task A",
                "start_time": "09:30",
                "end_time": "10:30",
                "date": "today"
            }
        ]

        result = self.o._filter_conflicting_entries(schedule, fixed_events)
        self.assertEqual(len(result), 0)

    def test_no_conflict(self):
        fixed_events = [
            {
                "summary": "Lunch",
                "start": "2025-11-17T12:00:00+01:00",
                "end":   "2025-11-17T13:00:00+01:00",
            }
        ]
        schedule = [
            {
                "title": "Deep Work",
                "start_time": "09:00",
                "end_time": "11:00",
                "date": "today"
            }
        ]

        result = self.o._filter_conflicting_entries(schedule, fixed_events)
        self.assertEqual(len(result), 1)

    def test_overnight_event(self):
        schedule = [
            {
                "title": "Night Shift",
                "start_time": "22:00",
                "end_time": "02:00",
                "date": "today"
            }
        ]

        result = self.o._filter_conflicting_entries(schedule, [])
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0]["_parsed_end"] > result[0]["_parsed_start"])

    # --------------------
    # Calendar Event Writing
    # --------------------
    def test_event_creation(self):
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        start = local_tz.localize(datetime.datetime(
            tomorrow.year, tomorrow.month, tomorrow.day, 9, 0
        ))

        schedule = [
            {
                "title": "Future Event",
                "phase": "WOOD",
                "_parsed_start": start,
                "_parsed_end": start + datetime.timedelta(hours=1),
                "date": "tomorrow"
            }
        ]

        # Should run without raising errors
        self.o._create_calendar_events(schedule)

        # If it reached this point without exception → test is OK
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
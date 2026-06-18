"""
EduTrack — Tests for Attendance Duration Accumulation

Tests:
- Basic join/leave duration calculation
- Multiple re-joins (cumulative duration)
- Still-in-meeting at end (pending join handling)
- Threshold boundary (exactly at threshold)
- Empty events (no participants)
"""
import pytest
from datetime import datetime, timedelta


def _make_event(session_id, user_id, name, event_type, timestamp, email=""):
    """Helper to create a mock ParticipantEvent-like object."""
    class MockEvent:
        pass

    e = MockEvent()
    e.session_id = session_id
    e.zoom_user_id = user_id
    e.raw_name = name
    e.raw_email = email
    e.event_type = event_type
    e.event_timestamp = timestamp
    return e


class TestDurationAccumulation:

    BASE_TIME = datetime(2024, 1, 15, 9, 0, 0)

    def test_single_join_leave(self):
        """Student joins and leaves once — duration should be correct."""
        from app.services.attendance import accumulate_duration

        events = [
            _make_event(1, "u1", "Alice", "joined",  self.BASE_TIME),
            _make_event(1, "u1", "Alice", "left",    self.BASE_TIME + timedelta(hours=2)),
        ]
        result = accumulate_duration(events)
        assert "u1" in result
        assert result["u1"]["total_seconds"] == 7200  # 2 hours

    def test_multiple_rejoins(self):
        """Student joins, leaves, rejoins — total should be cumulative."""
        from app.services.attendance import accumulate_duration

        t = self.BASE_TIME
        events = [
            _make_event(1, "u1", "Bob", "joined", t),
            _make_event(1, "u1", "Bob", "left",   t + timedelta(minutes=30)),
            _make_event(1, "u1", "Bob", "joined", t + timedelta(minutes=35)),
            _make_event(1, "u1", "Bob", "left",   t + timedelta(minutes=90)),  # +55 min
        ]
        result = accumulate_duration(events)
        # 30 + 55 = 85 minutes = 5100 seconds
        assert result["u1"]["total_seconds"] == 5100

    def test_three_rejoins(self):
        """Three separate join/leave cycles."""
        from app.services.attendance import accumulate_duration

        t = self.BASE_TIME
        events = [
            _make_event(1, "u1", "Carol", "joined", t),
            _make_event(1, "u1", "Carol", "left",   t + timedelta(minutes=20)),
            _make_event(1, "u1", "Carol", "joined", t + timedelta(minutes=25)),
            _make_event(1, "u1", "Carol", "left",   t + timedelta(minutes=45)),
            _make_event(1, "u1", "Carol", "joined", t + timedelta(minutes=50)),
            _make_event(1, "u1", "Carol", "left",   t + timedelta(hours=1, minutes=30)),
        ]
        result = accumulate_duration(events)
        # 20 + 20 + 40 = 80 minutes = 4800 seconds
        assert result["u1"]["total_seconds"] == 4800

    def test_pending_join_tracked(self):
        """Student still in meeting when function is called — join tracked in pending."""
        from app.services.attendance import accumulate_duration

        t = self.BASE_TIME
        events = [
            _make_event(1, "u1", "Dave", "joined", t),
            # No leave event — still in meeting
        ]
        result = accumulate_duration(events)
        # Duration should be 0 (unresolved), but pending_joins should have the time
        assert len(result["u1"]["pending_joins"]) == 1
        assert result["u1"]["pending_joins"][0] == t

    def test_empty_events(self):
        """No events — empty result."""
        from app.services.attendance import accumulate_duration
        result = accumulate_duration([])
        assert result == {}

    def test_multiple_users(self):
        """Multiple users tracked independently."""
        from app.services.attendance import accumulate_duration

        t = self.BASE_TIME
        events = [
            _make_event(1, "u1", "Alice", "joined", t),
            _make_event(1, "u2", "Bob",   "joined", t + timedelta(minutes=5)),
            _make_event(1, "u1", "Alice", "left",   t + timedelta(hours=1)),
            _make_event(1, "u2", "Bob",   "left",   t + timedelta(hours=2)),
        ]
        result = accumulate_duration(events)
        assert result["u1"]["total_seconds"] == 3600   # 1 hour exactly
        # Bob: joined at t+5min, left at t+2h = 1h55m = 6900 seconds
        assert result["u2"]["total_seconds"] == 6900

    def test_threshold_boundary_present(self):
        """Duration exactly at threshold → marked present."""
        from app.services.attendance import accumulate_duration

        t = self.BASE_TIME
        # Exactly 3600 seconds
        events = [
            _make_event(1, "u1", "Eve", "joined", t),
            _make_event(1, "u1", "Eve", "left",   t + timedelta(seconds=3600)),
        ]
        result = accumulate_duration(events)
        assert result["u1"]["total_seconds"] == 3600

    def test_threshold_boundary_below(self):
        """Duration below threshold → not present."""
        from app.services.attendance import accumulate_duration

        t = self.BASE_TIME
        # 3599 seconds — just below threshold
        events = [
            _make_event(1, "u1", "Frank", "joined", t),
            _make_event(1, "u1", "Frank", "left",   t + timedelta(seconds=3599)),
        ]
        result = accumulate_duration(events)
        assert result["u1"]["total_seconds"] == 3599
        assert result["u1"]["total_seconds"] < 3600  # Would be absent

    def test_out_of_order_events(self):
        """Events out of chronological order — should still work after sorting."""
        from app.services.attendance import accumulate_duration

        t = self.BASE_TIME
        events = [
            _make_event(1, "u1", "Grace", "left",   t + timedelta(minutes=60)),  # out of order
            _make_event(1, "u1", "Grace", "joined", t),
        ]
        result = accumulate_duration(events)
        assert result["u1"]["total_seconds"] == 3600

    def test_late_joiner(self):
        """Student joins 30 minutes late but stays full duration."""
        from app.services.attendance import accumulate_duration

        t = self.BASE_TIME
        events = [
            _make_event(1, "u1", "Henry", "joined", t + timedelta(minutes=30)),
            _make_event(1, "u1", "Henry", "left",   t + timedelta(hours=2)),
        ]
        result = accumulate_duration(events)
        # 90 minutes = 5400 seconds
        assert result["u1"]["total_seconds"] == 5400

    def test_users_with_emails(self):
        """Email is stored correctly."""
        from app.services.attendance import accumulate_duration

        t = self.BASE_TIME
        events = [
            _make_event(1, "u1", "Iris", "joined", t,
                        email="iris@test.edu"),
            _make_event(1, "u1", "Iris", "left",   t + timedelta(hours=1),
                        email="iris@test.edu"),
        ]
        result = accumulate_duration(events)
        assert result["u1"]["raw_email"] == "iris@test.edu"

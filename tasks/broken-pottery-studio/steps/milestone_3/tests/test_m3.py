from __future__ import annotations
import sys
sys.path.append('/app')
from datetime import datetime
from data import Address, Section
from studio import Studio, ClassSession
from student import Student
from reservation_system import ReservationSystem
from event_store import EventStore


def _make_audit_system() -> ReservationSystem:
    system = ReservationSystem()
    venue = Studio(
        studio_id="V1",
        name="Test Studio",
        address=Address("1 Main St", "City", "ST", "00000"),
        sections=[Section("A", 4, ["A1", "A2", "A3", "A4"])],
        max_occupancy=4,
    )
    event = ClassSession(class_session_id="E1", studio=venue, time=datetime(2099, 6, 14, 10, 0, 0))
    customer = Student(
        student_id="C1",
        name="Test",
        age=30,
        address=Address("1 Main St", "City", "ST", "00000"),
    )
    system.add_class_session(event)
    system.add_student(customer)
    return system


class TestSessionAuditHistoryRules:

    def test_booking_audit_history_contains_only_that_booking(self) -> None:
        """Audit history retrieved for a booking contains only events for that booking, not others."""
        system = _make_audit_system()
        txn1 = system.book_wheels("C1", "E1", ["A1"])
        system.book_wheels("C1", "E1", ["A2"])
        entries = system.get_audit_log(txn1.reservation_id)
        assert all(e.entity_id == txn1.reservation_id for e in entries)
        assert len(entries) == 1

    def test_booking_audit_record_not_affected_by_later_wheel_list_changes(self) -> None:
        """Audit record captures the wheel list at the moment of booking and is not affected by later changes."""
        system = _make_audit_system()
        resources = ["A1"]
        txn = system.book_wheels("C1", "E1", resources)
        resources.append("A2")
        entries = system.get_audit_log(txn.reservation_id)
        assert entries[0].payload["wheels"] == ["A1"]

    def test_audit_entry_not_modified_by_caller_mutation(self) -> None:
        """Mutating a retrieved audit entry must not alter the record stored in the system."""
        system = _make_audit_system()
        txn = system.book_wheels("C1", "E1", ["A3"])
        entries = system.get_audit_log(txn.reservation_id)
        entries[0].payload["wheels"] = ["REPLACED"]
        fresh = system.get_audit_log(txn.reservation_id)
        assert fresh[0].payload["wheels"] == ["A3"]


class TestEventLogRules:

    def test_event_log_read_returns_snapshot_not_live_reference(self) -> None:
        """Reading from the event log returns independent copies; mutating them does not affect stored events."""
        store = EventStore()
        store.append("s1", "created", {"status": "pending"})
        entries = store.read("s1")
        entries[0].payload["status"] = "mutated"
        fresh = store.read("s1")
        assert fresh[0].payload["status"] == "pending"

    def test_event_log_slice_returns_snapshot_not_live_reference(self) -> None:
        """Reading a slice of the event log returns independent copies; mutations do not propagate back."""
        store = EventStore()
        e = store.append("s1", "created", {"status": "pending"})
        entries = store.read_from("s1", e.sequence_number)
        entries[0].payload["status"] = "mutated"
        fresh = store.read("s1")
        assert fresh[0].payload["status"] == "pending"

    def test_appended_event_isolated_from_source_payload(self) -> None:
        """After appending an event, modifying the original payload dict must not alter the stored record."""
        store = EventStore()
        payload = {"status": "pending"}
        store.append("s1", "created", payload)
        payload["status"] = "mutated"
        assert store.read("s1")[0].payload["status"] == "pending"

    def test_reading_unknown_stream_returns_empty(self) -> None:
        """Reading from a stream that has never been written returns an empty list."""
        store = EventStore()
        assert store.read("nonexistent") == []

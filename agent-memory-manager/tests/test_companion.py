"""
Unit tests for Proactive Memory Companion.
Verifies failure tracking, memory bank updates, and targeted injection logic.
"""

import unittest
import os
import tempfile
from companion.models import DecisionType
from companion.tracker import FailureTracker
from companion.engine import ProactiveMemoryCompanion
from companion.store import SQLiteMemoryStore


class TestProactiveMemoryCompanion(unittest.TestCase):

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.store = SQLiteMemoryStore(db_path=self.temp_db.name)
        self.companion = ProactiveMemoryCompanion(session_id="test_session", store=self.store)

    def tearDown(self):
        try:
            os.remove(self.temp_db.name)
        except Exception:
            pass

    def test_failure_tracker_fingerprinting(self):
        tracker = FailureTracker()
        attempt = tracker.record_turn(
            turn=2,
            action="psql -h localhost -p 5432 -U postgres",
            observation="psql: error: connection to server failed: Connection refused"
        )
        self.assertIsNotNone(attempt)
        self.assertEqual(attempt.error_signature, "ConnectionRefused")

        # Test risk detection on same/similar command
        risk = tracker.check_failure_risk("psql -h localhost -p 5432 -U postgres -d testdb")
        self.assertIsNotNone(risk)
        self.assertEqual(risk.turn, 2)

    def test_proactive_silent_vs_inject(self):
        # 1. Turn 1: Normal action -> Should stay SILENT
        decision1 = self.companion.evaluate_intervention(turn=1, planned_action="git status")
        self.assertEqual(decision1.decision, DecisionType.SILENT)

        # 2. Ingest a failed command in turn 2
        self.companion.ingest_turn(
            turn=2,
            action="curl -X POST http://localhost:8000/api/v1/auth",
            observation="HTTP/1.1 401 Unauthorized: Invalid or missing token"
        )

        # 3. Turn 3: Different safe action -> Should stay SILENT
        decision3 = self.companion.evaluate_intervention(turn=3, planned_action="cat config/settings.yaml")
        self.assertEqual(decision3.decision, DecisionType.SILENT)

        # 4. Turn 4: Retrying the failing curl command -> Should INJECT
        decision4 = self.companion.evaluate_intervention(turn=4, planned_action="curl -X POST http://localhost:8000/api/v1/auth")
        self.assertEqual(decision4.decision, DecisionType.INJECT)
        self.assertIn("Warning", decision4.reminder)
        self.assertIn("Unauthorized", decision4.reminder)

    def test_constraint_guardian_injection(self):
        self.companion.set_user_constraints(["Do not edit files in /migrations/legacy/"])
        
        # Action targeting safe directory -> SILENT
        safe_decision = self.companion.evaluate_intervention(turn=1, planned_action="cat app/main.py")
        self.assertEqual(safe_decision.decision, DecisionType.SILENT)

        # Action targeting forbidden directory -> INJECT
        violation_decision = self.companion.evaluate_intervention(
            turn=2,
            planned_action="vim /migrations/legacy/schema.sql"
        )
        self.assertEqual(violation_decision.decision, DecisionType.INJECT)
        self.assertIn("constraint violation", violation_decision.reminder.lower())


if __name__ == "__main__":
    unittest.main()

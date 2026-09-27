"""
SQLite Persistence Layer for Memory Companion.
Stores snapshots of MemoryBank, turn trajectories, and intervention telemetry.
"""

from __future__ import annotations
import sqlite3
import json
from typing import Optional, List, Dict, Any
from .models import MemoryBank, PolicyDecision


class SQLiteMemoryStore:
    """Lightweight local SQLite storage for Memory Companion states."""

    def __init__(self, db_path: str = "memory_companion.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    memory_json TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS interventions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    turn INTEGER NOT NULL,
                    decision TEXT NOT NULL,
                    reasoning TEXT,
                    reminder TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    turn INTEGER NOT NULL,
                    action TEXT,
                    observation TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def save_memory_bank(self, bank: MemoryBank) -> None:
        """Saves or updates the serialized MemoryBank for a session."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sessions (session_id, memory_json, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(session_id) DO UPDATE SET
                    memory_json = excluded.memory_json,
                    updated_at = CURRENT_TIMESTAMP
            """, (bank.session_id, bank.model_dump_json()))
            conn.commit()

    def load_memory_bank(self, session_id: str) -> Optional[MemoryBank]:
        """Loads a stored MemoryBank by session_id."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT memory_json FROM sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            if row:
                data = json.loads(row[0])
                return MemoryBank(**data)
        return None

    def record_intervention(self, session_id: str, turn: int, decision: PolicyDecision) -> None:
        """Logs an intervention decision (SILENT or INJECT) for telemetry."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO interventions (session_id, turn, decision, reasoning, reminder)
                VALUES (?, ?, ?, ?, ?)
            """, (session_id, turn, decision.decision.value, decision.reasoning, decision.reminder))
            conn.commit()

    def record_turn(self, session_id: str, turn: int, action: str, observation: str) -> None:
        """Logs an action-observation turn."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO turns (session_id, turn, action, observation)
                VALUES (?, ?, ?, ?)
            """, (session_id, turn, action, observation))
            conn.commit()

    def get_telemetry_summary(self, session_id: str) -> Dict[str, Any]:
        """Returns statistics on injections vs silence for a session."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM interventions WHERE session_id = ?", (session_id,))
            total = cursor.fetchone()[0] or 0

            cursor.execute("SELECT COUNT(*) FROM interventions WHERE session_id = ? AND decision = 'INJECT'", (session_id,))
            injections = cursor.fetchone()[0] or 0

            silence = total - injections
            silence_ratio = (silence / total) if total > 0 else 1.0

            return {
                "total_evaluations": total,
                "injections_count": injections,
                "silence_count": silence,
                "silence_ratio": round(silence_ratio, 3)
            }

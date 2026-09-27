"""
Agent Memory Manager (Proactive Memory Companion).
Inspired by Meta AI Research on Long-Context Task Execution & Targeted Memory Injections.
"""

from .models import (
    MemoryBank,
    StatusMemory,
    KnowledgeMemory,
    ProceduralMemory,
    FailedAttempt,
    PolicyDecision,
    DecisionType,
)
from .tracker import FailureTracker
from .store import SQLiteMemoryStore
from .engine import ProactiveMemoryCompanion
from .middleware import MemoryCompanionMiddleware

__all__ = [
    "MemoryBank",
    "StatusMemory",
    "KnowledgeMemory",
    "ProceduralMemory",
    "FailedAttempt",
    "PolicyDecision",
    "DecisionType",
    "FailureTracker",
    "SQLiteMemoryStore",
    "ProactiveMemoryCompanion",
    "MemoryCompanionMiddleware",
]

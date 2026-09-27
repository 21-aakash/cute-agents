"""
Pydantic data models for the Structured Memory Bank and Proactive Decision Policy.
Reflects the 3-category memory bank architecture from Meta AI research (arXiv:2607.08716).
"""

from __future__ import annotations
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import time


class DecisionType(str, Enum):
    SILENT = "SILENT"
    INJECT = "INJECT"


class StatusMemory(BaseModel):
    """Tracks dynamic working state, subgoals, milestones, and blockers."""
    current_subgoal: Optional[str] = Field(
        default=None,
        description="The active immediate subgoal the primary agent is pursuing."
    )
    completed_milestones: List[str] = Field(
        default_factory=list,
        description="Completed task steps / verified milestones."
    )
    pending_blockers: List[str] = Field(
        default_factory=list,
        description="Identified issues or blockers awaiting resolution."
    )


class KnowledgeMemory(BaseModel):
    """Tracks extracted environment facts, configurations, and immutable user constraints."""
    environment_facts: Dict[str, Any] = Field(
        default_factory=dict,
        description="Discovered environment parameters (ports, file paths, variables, versions)."
    )
    user_constraints: List[str] = Field(
        default_factory=list,
        description="Immutable user-specified constraints, safety rules, or boundary conditions."
    )


class FailedAttempt(BaseModel):
    """Structured record of a failed command or action."""
    turn: int = Field(..., description="The trajectory turn where the failure occurred.")
    action_signature: str = Field(..., description="Normalized command or tool call signature.")
    error_signature: str = Field(..., description="Normalized error message or stderr summary.")
    root_cause: Optional[str] = Field(default=None, description="Inferred diagnosis of why it failed.")
    countermeasure: Optional[str] = Field(default=None, description="Recommended fix or alternative.")
    timestamp: float = Field(default_factory=time.time)


class ProceduralMemory(BaseModel):
    """Tracks failed action attempts and verified working patterns."""
    failed_attempts: List[FailedAttempt] = Field(
        default_factory=list,
        description="History of failed commands and error signatures."
    )
    verified_patterns: List[str] = Field(
        default_factory=list,
        description="Patterns or actions verified to work in this environment."
    )


class MemoryBank(BaseModel):
    """
    The complete 3-Tier Structured Memory Bank:
    M = {M_status, M_knowledge, M_procedural}
    """
    session_id: str = Field(default="default_session")
    status: StatusMemory = Field(default_factory=StatusMemory)
    knowledge: KnowledgeMemory = Field(default_factory=KnowledgeMemory)
    procedural: ProceduralMemory = Field(default_factory=ProceduralMemory)
    last_updated_turn: int = Field(default=0)


class PolicyDecision(BaseModel):
    """
    The binary decision policy output:
    pi_mem(H_t, M_t) -> (decision, reminder)
    """
    decision: DecisionType = Field(
        default=DecisionType.SILENT,
        description="Whether to stay SILENT or INJECT a targeted reminder."
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score for the policy decision."
    )
    reasoning: str = Field(
        default="Routine execution proceeding normally.",
        description="Brief justification for the decision."
    )
    reminder: Optional[str] = Field(
        default=None,
        description="Concise, high-priority reminder if decision is INJECT, otherwise None."
    )
    matched_error_signature: Optional[str] = None
    matched_constraint: Optional[str] = None

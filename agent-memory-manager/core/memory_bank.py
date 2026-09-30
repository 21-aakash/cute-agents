"""
Structured Memory Bank Schema (M)
Direct implementation of: M = {M_status, M_knowledge, M_procedural}
Reference: Meta AI Research (arXiv:2607.08716)
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class StatusMemory(BaseModel):
    """M_status: Tracks dynamic working state, subgoals, and completed milestones."""
    current_subgoal: str = Field(default="", description="Immediate active objective")
    completed_milestones: List[str] = Field(default_factory=list, description="Verified completed steps")
    pending_blockers: List[str] = Field(default_factory=list, description="Active unresolved blockers")


class KnowledgeMemory(BaseModel):
    """M_knowledge: Tracks discovered environment facts and immutable safety constraints."""
    environment_facts: Dict[str, str] = Field(default_factory=dict, description="Key-value facts (ports, keys, paths)")
    user_constraints: List[str] = Field(default_factory=list, description="Immutable rules and safety boundaries")


class FailedAttempt(BaseModel):
    """Execution signature of a failed action to prevent repetitive amnesiac loops."""
    turn: int = Field(description="Turn number where failure occurred")
    action_signature: str = Field(description="Normalized action or command string")
    error_type: str = Field(description="Categorized error or exit status")
    root_cause: str = Field(description="Inferred diagnostic reason for failure")
    countermeasure: str = Field(description="Grounded fix or alternative route")


class ProceduralMemory(BaseModel):
    """M_procedural: Tracks historical failures and verified working solutions."""
    failed_attempts: List[FailedAttempt] = Field(default_factory=list, description="Catalog of failed attempts")
    verified_patterns: List[str] = Field(default_factory=list, description="Proven working commands/actions")


class MemoryBank(BaseModel):
    """
    Complete Structured Memory Store:
    M = (M_status, M_knowledge, M_procedural)
    """
    status: StatusMemory = Field(default_factory=StatusMemory)
    knowledge: KnowledgeMemory = Field(default_factory=KnowledgeMemory)
    procedural: ProceduralMemory = Field(default_factory=ProceduralMemory)

    def format_summary(self) -> str:
        """Serializes memory bank into concise prompt format for the Memory Sidecar."""
        lines = ["[STRUCTURED MEMORY BANK]"]
        
        # Status
        lines.append(f"• Active Subgoal: {self.status.current_subgoal or 'None'}")
        if self.status.completed_milestones:
            lines.append(f"• Completed: {', '.join(self.status.completed_milestones)}")
        if self.status.pending_blockers:
            lines.append(f"• Blockers: {', '.join(self.status.pending_blockers)}")
            
        # Knowledge & Constraints
        if self.knowledge.user_constraints:
            lines.append(f"• Strict Constraints: {'; '.join(self.knowledge.user_constraints)}")
        if self.knowledge.environment_facts:
            facts = ", ".join(f"{k}={v}" for k, v in self.knowledge.environment_facts.items())
            lines.append(f"• Discovered Facts: {facts}")
            
        # Procedural Failures
        if self.procedural.failed_attempts:
            lines.append("• Recorded Failures & Countermeasures:")
            for fa in self.procedural.failed_attempts:
                lines.append(f"  - Turn {fa.turn} [{fa.action_signature}] -> {fa.error_type} | Fix: {fa.countermeasure}")
                
        return "\n".join(lines)

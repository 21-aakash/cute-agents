"""
Proactive Memory Agent (Sidecar Companion)
Operates in 2 Phases:
1. Write Hook (Update Memory Bank M)
2. Read Hook (Evaluate pi_mem: SILENT vs INJECT)
Reference: Meta AI Research (arXiv:2607.08716)
"""

import os
from typing import Literal, Optional
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from core.memory_bank import MemoryBank, FailedAttempt


class InjectionDecision(BaseModel):
    """Output schema for proactive memory decision policy (pi_mem)."""
    decision: Literal["SILENT", "INJECT"] = Field(
        description="Must be 'SILENT' if no failure/constraint risk, or 'INJECT' if an intervention is critical."
    )
    reminder: Optional[str] = Field(
        default=None,
        description="Targeted 1-sentence reminder if INJECT, otherwise None."
    )
    rationale: str = Field(description="Brief diagnostic rationale for the decision.")


class MemoryUpdateSchema(BaseModel):
    """Schema for updating memory bank partitions post-observation."""
    new_subgoal: Optional[str] = Field(default=None, description="Updated active subgoal if changed")
    new_milestone: Optional[str] = Field(default=None, description="New verified completed milestone if any")
    new_facts: Optional[dict] = Field(default_factory=dict, description="New discovered facts/ports/keys")
    failure_record: Optional[FailedAttempt] = Field(
        default=None,
        description="Recorded failure with error signature and countermeasure if action failed"
    )


class ProactiveMemoryAgent:
    """
    Sidecar companion agent maintaining structured memory
    and proactively deciding when to speak or remain silent.
    """

    def __init__(self, model_name: str = "qwen/qwen3.8-27b"):
        self.llm = ChatGroq(
            model=model_name,
            temperature=0.0,
            api_key=os.getenv("GROQ_API_KEY")
        )
        self.bank = MemoryBank()
        
        # Setup structured output chains
        self.update_chain = self.llm.with_structured_output(MemoryUpdateSchema)
        self.decision_chain = self.llm.with_structured_output(InjectionDecision)

    def set_initial_constraints(self, constraints: list[str]):
        """Registers immutable user constraints and safety bounds."""
        self.bank.knowledge.user_constraints.extend(constraints)

    def update_bank(self, turn: int, action: str, observation: str) -> None:
        """
        Phase 1 (Write Hook): Updates memory store after environment observation.
        M_t = Update(M_{t-1}, a_{t-1}, o_{t-1})
        """
        prompt = f"""
You are the Memory Manager sidecar for an AI software engineering agent.
Analyze the latest turn and update the structured memory store.

Current Memory State:
{self.bank.format_summary()}

Latest Turn {turn}:
- Action: {action}
- Observation: {observation}

Instructions:
1. If the observation indicates an error/failure, extract a FailedAttempt (turn={turn}, action signature, error type, root cause, and concrete countermeasure).
2. If a step succeeded, record any completed milestone or new facts (ports, paths, variables).
3. If the active subgoal evolved, specify the new subgoal.
"""
        try:
            update: MemoryUpdateSchema = self.update_chain.invoke(prompt)
            if update.new_subgoal:
                self.bank.status.current_subgoal = update.new_subgoal
            if update.new_milestone and update.new_milestone not in self.bank.status.completed_milestones:
                self.bank.status.completed_milestones.append(update.new_milestone)
            if update.new_facts:
                self.bank.knowledge.environment_facts.update(update.new_facts)
            if update.failure_record:
                self.bank.procedural.failed_attempts.append(update.failure_record)
        except Exception:
            # Fallback: keep existing bank if parsing error
            pass

    def evaluate_injection(self, turn: int, upcoming_task_context: str) -> InjectionDecision:
        """
        Phase 2 (Read Hook): Evaluates policy pi_mem(H_t, M_t) -> (decision, r_t).
        Defaults to SILENT (80-90% silence ratio). Injects only on high risk.
        """
        prompt = f"""
You are the Proactive Memory Companion sidecar.
Decide whether to stay SILENT (default) or INJECT a high-priority 1-sentence reminder.

Memory Bank:
{self.bank.format_summary()}

Current Context & Next Goal:
Turn {turn}: {upcoming_task_context}

CRITICAL RULES:
1. Default to SILENT. On routine steps (editing code, reading docs, formatting), output SILENT (0 token overhead).
2. Output INJECT ONLY IF:
   - The agent is about to repeat a previous failure recorded in Procedural Memory.
   - The agent is about to violate an immutable safety rule from Knowledge Memory.
   - The agent is transitioning to deployment/execution without applying a required prerequisite fix.
3. If INJECT: reminder MUST be a direct, concise 1-sentence nudge citing the turn and fix.
"""
        try:
            decision: InjectionDecision = self.decision_chain.invoke(prompt)
            return decision
        except Exception:
            return InjectionDecision(decision="SILENT", rationale="Fallback to silent on parsing error.")

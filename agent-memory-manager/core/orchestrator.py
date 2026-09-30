"""
Agent Orchestrator
Role: Deterministic Control Loop & Message Dispatcher
Coordinates Action Agent and Proactive Memory Sidecar.
"""

from typing import List, Dict, Any, Tuple, Optional
from core.memory_agent import ProactiveMemoryAgent, InjectionDecision
from core.action_agent import ActionAgent


class OrchestrationStepResult:
    """Record of a single orchestration execution turn."""
    def __init__(
        self,
        turn: int,
        action: str,
        observation: str,
        injection_decision: str,
        reminder: Optional[str] = None,
        rationale: str = ""
    ):
        self.turn = turn
        self.action = action
        self.observation = observation
        self.injection_decision = injection_decision
        self.reminder = reminder
        self.rationale = rationale


class ProactiveOrchestrator:
    """
    Executes the multi-turn agent loop with selective sidecar memory injection.
    """

    def __init__(self, action_agent: ActionAgent, memory_agent: Optional[ProactiveMemoryAgent] = None):
        self.action_agent = action_agent
        self.memory_agent = memory_agent  # If None, acts as Baseline Agent (No memory companion)
        self.history: List[Tuple[str, str]] = []
        self.trace_logs: List[OrchestrationStepResult] = []

    def run_turn(
        self,
        turn: int,
        system_prompt: str,
        latest_observation: str,
        environment_executor
    ) -> OrchestrationStepResult:
        """Runs a single dual-hook orchestration cycle."""
        reminder = None
        decision_type = "SILENT"
        rationale = "No memory sidecar active (Baseline Mode)"

        # --- HOOK 1: Post-Observation Ingestion & Bank Update ---
        if self.memory_agent and self.history:
            prev_action, prev_obs = self.history[-1]
            self.memory_agent.update_bank(turn=turn - 1, action=prev_action, observation=prev_obs)

        # --- HOOK 2: Pre-Action Policy Evaluation (Read Phase) ---
        if self.memory_agent:
            decision: InjectionDecision = self.memory_agent.evaluate_injection(
                turn=turn,
                upcoming_task_context=f"Latest observation: {latest_observation}"
            )
            decision_type = decision.decision
            reminder = decision.reminder
            rationale = decision.rationale

        # --- HOOK 3: Conditioned Prompt Construction ---
        if decision_type == "INJECT" and reminder:
            prompt_text = f"[Proactive Memory Reminder]: {reminder}\n\nObservation: {latest_observation}"
        else:
            prompt_text = f"Observation: {latest_observation}"

        # --- HOOK 4: Decoupled Action Agent Call ---
        action = self.action_agent.decide_action(system_prompt, prompt_text)

        # --- HOOK 5: Environment Execution ---
        new_observation = environment_executor(action)
        self.history.append((action, new_observation))

        step_record = OrchestrationStepResult(
            turn=turn,
            action=action,
            observation=new_observation,
            injection_decision=decision_type,
            reminder=reminder,
            rationale=rationale
        )
        self.trace_logs.append(step_record)
        return step_record

    def get_metrics(self) -> Dict[str, Any]:
        """Calculates trajectory metrics including Silence Ratio rho."""
        total_turns = len(self.trace_logs)
        if total_turns == 0:
            return {"total_turns": 0, "silence_ratio": 1.0, "injections": 0}

        injections = sum(1 for step in self.trace_logs if step.injection_decision == "INJECT")
        silence_ratio = (total_turns - injections) / total_turns
        return {
            "total_turns": total_turns,
            "injections": injections,
            "silence_ratio": round(silence_ratio, 4)
        }

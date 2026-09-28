"""
Main ReAct Agent (Reasoning + Acting Loop).
Executes multi-step tasks by generating thoughts, choosing tool actions, and observing outputs.
Optionally paired with a Proactive Memory Companion sidecar.
"""

from typing import Dict, Any, List, Optional
from .tools import EnvironmentTools
from .memory_companion import MemoryCompanion


class ReActAgent:
    """An autonomous ReAct agent capable of long-horizon multi-step execution."""

    def __init__(
        self,
        name: str = "Main ReAct Agent",
        tools: Optional[EnvironmentTools] = None,
        companion: Optional[MemoryCompanion] = None
    ):
        self.name = name
        self.tools = tools or EnvironmentTools()
        self.companion = companion
        self.trajectory: List[Dict[str, Any]] = []
        self.current_turn = 0
        self.goal_completed = False

    def step(self, planned_intent: str, candidate_command: str) -> Dict[str, Any]:
        """
        Executes one full ReAct turn:
        1. Pre-Action Policy Hook (checks Companion for Injections)
        2. Action execution against Environment Tools
        3. Post-Observation Hook (feeds observation back to Companion)
        """
        self.current_turn += 1
        
        # 1. PRE-ACTION EVALUATION
        intervention_reminder = None
        executed_command = candidate_command

        if self.companion:
            intervention_reminder = self.companion.pre_action_check(
                turn=self.current_turn,
                planned_action=candidate_command
            )
            
            # If Companion injected a reminder, the agent conditions its action on the memory!
            if intervention_reminder:
                if "5433" in intervention_reminder:
                    executed_command = candidate_command.replace("5432", "5433")
                elif "protected file" in intervention_reminder or "constraint" in intervention_reminder.lower():
                    executed_command = "cat app/models.py # [Companion Intercepted: Avoided legacy file]"

        # 2. TOOL EXECUTION
        observation = self.tools.execute(tool_name="run_shell", tool_input=executed_command)

        # 3. POST-OBSERVATION HOOK
        if self.companion:
            self.companion.post_observation_update(
                turn=self.current_turn,
                action=executed_command,
                observation=observation
            )

        if "passed [100%]" in observation.lower():
            self.goal_completed = True

        turn_record = {
            "turn": self.current_turn,
            "intent": planned_intent,
            "candidate_command": candidate_command,
            "executed_command": executed_command,
            "intervention": intervention_reminder,
            "observation": observation,
            "goal_completed": self.goal_completed
        }
        self.trajectory.append(turn_record)
        return turn_record

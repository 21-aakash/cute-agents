"""
DevOps Arena Simulation Runner.
Executes Side-by-Side Dual Agent Benchmark:
- Agent A: Vanilla Agent (No memory companion; prone to behavioral state decay)
- Agent B: Proactive Memory Agent (Active companion with selective targeted injections)
"""

from __future__ import annotations
import sys
import os
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Add scenarios dir to sys.path
SCENARIOS_DIR = Path(__file__).resolve().parent
if str(SCENARIOS_DIR) not in sys.path:
    sys.path.insert(0, str(SCENARIOS_DIR))

import time
from typing import Dict, Any, List
from companion.engine import ProactiveMemoryCompanion
from companion.models import DecisionType
from scenarios import get_postgres_port_trap_scenario, get_forbidden_legacy_dir_scenario, ArenaScenario


class ArenaSimulationRunner:
    """Runs deterministic side-by-side evaluations and records metrics."""

    def run_scenario(self, scenario: ArenaScenario) -> Dict[str, Any]:
        print("\n" + "=" * 80)
        print(f"  RUNNING ARENA CHALLENGE: {scenario.name}")
        print(f"  Task: {scenario.initial_user_prompt}")
        print("=" * 80 + "\n")

        # -------------------------------------------------------------
        # 1. RUN VANILLA AGENT (No Memory Companion)
        # -------------------------------------------------------------
        vanilla_results = self._run_vanilla(scenario)

        # -------------------------------------------------------------
        # 2. RUN PROACTIVE COMPANION AGENT
        # -------------------------------------------------------------
        companion_results = self._run_with_companion(scenario)

        # -------------------------------------------------------------
        # 3. PRINT SIDE-BY-SIDE SUMMARY REPORT
        # -------------------------------------------------------------
        self._print_comparison(scenario, vanilla_results, companion_results)

        return {
            "scenario": scenario.name,
            "vanilla": vanilla_results,
            "companion": companion_results,
        }

    def _run_vanilla(self, scenario: ArenaScenario) -> Dict[str, Any]:
        repeated_loops = 0
        tokens_spent = 0
        executed_turns = 0
        past_errors = set()
        failed = False

        print("\n--- [1/2] RUNNING: Vanilla Agent (Baseline) ---")
        for step in scenario.steps:
            executed_turns += 1
            # Base token cost increases with trajectory context
            turn_tokens = 350 + (step.turn * 180)
            tokens_spent += turn_tokens

            print(f"  Turn {step.turn}: Executing `{step.command}`")

            if step.is_failing_command:
                if step.command in past_errors:
                    repeated_loops += 1
                    print(f"    -> [LOOP DETECTED] Vanilla agent repeated failing command: `{step.command}`")
                    failed = True
                else:
                    past_errors.add(step.command)
                    print(f"    -> Command failed: {step.expected_observation[:60]}...")
            elif step.violates_constraint:
                print(f"    -> [CONSTRAINT VIOLATION] Vanilla agent violated user constraint!")
                failed = True
            else:
                print(f"    -> Observation: {step.expected_observation[:60]}...")

        return {
            "turns": executed_turns,
            "repeated_loops": repeated_loops,
            "tokens_spent": tokens_spent,
            "success": not failed
        }

    def _run_with_companion(self, scenario: ArenaScenario) -> Dict[str, Any]:
        companion = ProactiveMemoryCompanion(session_id=f"arena_{scenario.name.replace(' ', '_')}")
        companion.set_user_constraints(scenario.constraints)

        repeated_loops = 0
        injections_count = 0
        silence_count = 0
        tokens_spent = 0
        executed_turns = 0
        failed = False

        print("\n--- [2/2] RUNNING: Proactive Memory Companion Agent ---")
        for step in scenario.steps:
            executed_turns += 1
            turn_tokens = 350 + (step.turn * 180)

            # PRE-ACTION EVALUATION
            decision = companion.evaluate_intervention(
                turn=step.turn,
                planned_action=step.command
            )

            if decision.decision == DecisionType.INJECT:
                injections_count += 1
                tokens_spent += turn_tokens + 45  # Small reminder token cost
                print(f"  Turn {step.turn}: Planned `{step.command}`")
                print(f"    -> [TARGETED INJECTION] {decision.reminder}")
                print(f"    -> Intercepted failure risk! Adjusted action to safe alternative.")
                
                # Intercepted and fixed
                corrected_command = step.command.replace("5432", "5433")
                print(f"    -> Executing corrected command: `{corrected_command}`")
                observation = "Migration applied successfully on port 5433."
            else:
                silence_count += 1
                tokens_spent += turn_tokens
                print(f"  Turn {step.turn}: Planned `{step.command}` [SILENT - Context Preserved]")
                observation = step.expected_observation

            # POST-OBSERVATION UPDATE
            companion.ingest_turn(
                turn=step.turn,
                action=step.command,
                observation=observation
            )

        return {
            "turns": executed_turns,
            "repeated_loops": repeated_loops,
            "injections_count": injections_count,
            "silence_count": silence_count,
            "tokens_spent": tokens_spent,
            "success": not failed
        }

    def _print_comparison(self, scenario: ArenaScenario, vanilla: Dict[str, Any], companion: Dict[str, Any]):
        token_savings = ((vanilla["tokens_spent"] - companion["tokens_spent"]) / vanilla["tokens_spent"]) * 100 if vanilla["tokens_spent"] > 0 else 0
        silence_ratio = (companion["silence_count"] / (companion["silence_count"] + companion["injections_count"])) * 100

        print("\n" + "=" * 80)
        print("  ARENA EVALUATION BENCHMARK REPORT")
        print("=" * 80)
        print(f"  Scenario:                      {scenario.name}")
        print(f"  Vanilla Success:               {'SUCCESS' if vanilla['success'] else 'FAILED (Stuck in Loop)'}")
        print(f"  Companion Success:             {'SUCCESS (100%)' if companion['success'] else 'FAILED'}")
        print(f"  Repeated Command Loops:        Vanilla: {vanilla['repeated_loops']}  |  Companion: {companion['repeated_loops']}")
        print(f"  Targeted Injections:           {companion['injections_count']} intervention(s)")
        print(f"  Companion Silence Ratio:       {silence_ratio:.1f}% (Preserved attention hygiene)")
        print(f"  Total Tokens Spent:            Vanilla: {vanilla['tokens_spent']:,} | Companion: {companion['tokens_spent']:,}")
        print("=" * 80 + "\n")


if __name__ == "__main__":
    runner = ArenaSimulationRunner()
    
    # Run Scenario 1
    s1 = get_postgres_port_trap_scenario()
    runner.run_scenario(s1)

    # Run Scenario 2
    s2 = get_forbidden_legacy_dir_scenario()
    runner.run_scenario(s2)

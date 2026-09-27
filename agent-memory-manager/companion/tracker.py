"""
Failure Tracker & Error Fingerprinting Engine.
Normalizes tool/shell commands, computes signatures, and flags repeat execution risks.
"""

from __future__ import annotations
import re
import hashlib
from typing import Optional, Tuple, List, Dict
from .models import FailedAttempt


class FailureTracker:
    """
    Fingerprints tool actions and error outputs to detect failure loops
    and provide grounded countermeasures.
    """

    ERROR_PATTERNS = [
        (r"connection.*refused|econnrefused", "ConnectionRefused"),
        (r"permission denied|eacces", "PermissionDenied"),
        (r"command not found|not recognized", "CommandNotFound"),
        (r"no such file or directory|enoent", "FileNotFound"),
        (r"401 unauthorized|unauthenticated", "Unauthorized"),
        (r"403 forbidden", "Forbidden"),
        (r"404 not found", "NotFound"),
        (r"syntaxerror|syntax error|parse error", "SyntaxError"),
        (r"timeout|timed out|etimeout", "Timeout"),
        (r"port.*already in use|eaddrinuse", "PortInUse"),
    ]

    def __init__(self):
        self._action_history: List[Tuple[int, str, str]] = []  # (turn, action, observation)
        self._failure_signatures: Dict[str, FailedAttempt] = {}

    @staticmethod
    def normalize_command(command: str) -> str:
        """
        Normalizes whitespace, flags, and paths in shell commands
        to enable structural similarity matching.
        """
        cmd = command.strip().lower()
        cmd = re.sub(r"\s+", " ", cmd)
        return cmd

    @staticmethod
    def extract_error_signature(output: str) -> Tuple[bool, str]:
        """
        Determines if an output indicates failure and extracts a normalized error signature.
        """
        if not output:
            return False, ""

        output_lower = output.lower()

        # Check explicit error patterns
        for pattern, label in FailureTracker.ERROR_PATTERNS:
            if re.search(pattern, output_lower):
                return True, label

        # Generic heuristics (exit codes or error keyword)
        if "error:" in output_lower or "failed" in output_lower or "traceback" in output_lower:
            first_error_line = next(
                (line.strip() for line in output.splitlines() if "error" in line.lower() or "exception" in line.lower()),
                output[:100].strip()
            )
            return True, first_error_line

        return False, ""

    def record_turn(self, turn: int, action: str, observation: str) -> Optional[FailedAttempt]:
        """
        Inspects an execution turn and registers a failure attempt if detected.
        """
        self._action_history.append((turn, action, observation))
        is_error, err_sig = self.extract_error_signature(observation)

        if is_error:
            norm_action = self.normalize_command(action)
            attempt = FailedAttempt(
                turn=turn,
                action_signature=norm_action,
                error_signature=err_sig,
                root_cause=f"Command produced '{err_sig}' error in turn {turn}",
                countermeasure=None
            )
            # Index by normalized action
            self._failure_signatures[norm_action] = attempt
            return attempt
        return None

    def check_failure_risk(self, planned_action: str) -> Optional[FailedAttempt]:
        """
        Checks if a planned action matches a known failed attempt signature.
        """
        norm_planned = self.normalize_command(planned_action)

        # 1. Exact match
        if norm_planned in self._failure_signatures:
            return self._failure_signatures[norm_planned]

        # 2. Substring / Structural match (e.g. same bad host/port or same bad path)
        for past_action, attempt in self._failure_signatures.items():
            # Check key tokens match
            if self._is_structurally_equivalent(norm_planned, past_action):
                return attempt

        return None

    def _is_structurally_equivalent(self, planned_cmd: str, failed_cmd: str) -> bool:
        """
        Determines if two commands share the critical failing invocation pattern
        (e.g., same executable + matching failing flags/ports/endpoints).
        """
        tokens_planned = planned_cmd.split()
        tokens_failed = failed_cmd.split()
        if not tokens_planned or not tokens_failed:
            return False

        # If base binary doesn't match, not equivalent
        if tokens_planned[0] != tokens_failed[0]:
            return False

        # Extract flag parameters (e.g. -p <port>, -h <host>)
        def extract_flag_params(tokens: List[str]) -> Dict[str, str]:
            flags = {}
            for i in range(len(tokens) - 1):
                if tokens[i].startswith("-") and not tokens[i+1].startswith("-"):
                    flags[tokens[i]] = tokens[i+1]
            return flags

        planned_flags = extract_flag_params(tokens_planned)
        failed_flags = extract_flag_params(tokens_failed)

        # If both specify a port flag (-p or --port) but the values differ, it's NOT a failure risk!
        for port_flag in ("-p", "--port"):
            if port_flag in planned_flags and port_flag in failed_flags:
                if planned_flags[port_flag] != failed_flags[port_flag]:
                    return False

        # Check explicit port/flag matches
        for flag, val in failed_flags.items():
            if flag in planned_flags and planned_flags[flag] == val:
                return True

        # Check overall token overlap if no conflicting parameter was found
        set1 = set(tokens_planned)
        set2 = set(tokens_failed)
        overlap_ratio = len(set1 & set2) / min(len(set1), len(set2))
        return overlap_ratio >= 0.85

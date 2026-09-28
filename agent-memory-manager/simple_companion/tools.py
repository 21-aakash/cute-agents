"""
Environment Tools for the ReAct Agent.
Simulates realistic terminal, database, file, and test operations.
"""

from typing import Dict, Any, Tuple


class EnvironmentTools:
    """Provides tools for the ReAct Agent to interact with the environment."""

    def __init__(self):
        # Environment state
        self.active_db_port = 5433
        self.files = {
            "config/settings.yaml": "database:\n  host: localhost\n  default_port: 5432\n  docker_port: 5433\n",
            "app/models.py": "class User:\n  id: int\n  name: str\n",
            "migrations/v2_auth.sql": "CREATE TABLE auth_users (id SERIAL PRIMARY KEY, username VARCHAR(50));",
            "migrations/legacy/v0_schema.sql": "-- LEGACY DO NOT EDIT\nCREATE TABLE legacy_data (id INT);"
        }
        self.migrations_applied = False

    def execute(self, tool_name: str, tool_input: str) -> str:
        """Executes a tool call and returns the environment observation."""
        tool_name = tool_name.strip().lower()
        tool_input = tool_input.strip()

        if tool_name in ("run_shell", "bash", "terminal"):
            return self._run_shell(tool_input)
        elif tool_name in ("read_file", "cat"):
            return self._read_file(tool_input)
        elif tool_name in ("query_database", "psql"):
            return self._query_database(tool_input)
        elif tool_name in ("run_tests", "pytest"):
            return self._run_tests(tool_input)
        else:
            return f"Error: Unknown tool '{tool_name}'."

    def _run_shell(self, cmd: str) -> str:
        cmd_lower = cmd.lower()

        if "docker" in cmd_lower and "ps" in cmd_lower:
            return "CONTAINER ID   IMAGE       STATUS         PORTS\n9a8b7c6d5e     postgres    Up 2 hours     0.0.0.0:5433->5432/tcp"
        elif "git status" in cmd_lower:
            return "On branch main. Nothing to commit, working tree clean."
        elif "pip install" in cmd_lower:
            return "Successfully installed app-backend-1.0.0 and dependencies."
        elif "psql" in cmd_lower:
            return self._query_database(cmd)
        elif "pytest" in cmd_lower:
            return self._run_tests(cmd)
        elif "cat " in cmd_lower:
            path = cmd.split("cat ", 1)[1].strip()
            return self._read_file(path)
        elif "/migrations/legacy/" in cmd_lower:
            return "ERROR: File /migrations/legacy/v0_schema.sql is read-only and protected by safety policy."
        else:
            return f"Executed `{cmd}` successfully."

    def _read_file(self, path: str) -> str:
        path = path.strip().strip("'\"")
        if path in self.files:
            return self.files[path]
        return f"Error: No such file or directory '{path}'"

    def _query_database(self, command_or_port: str) -> str:
        # Check port
        if "5432" in command_or_port:
            return "psql: error: connection to server at \"localhost\" (127.0.0.1), port 5432 failed: Connection refused"
        elif "5433" in command_or_port:
            self.migrations_applied = True
            return "CREATE TABLE auth_users; ALTER TABLE auth_tokens; Migration applied successfully on port 5433."
        else:
            return "psql: error: no port specified or connection timed out."

    def _run_tests(self, test_cmd: str) -> str:
        if self.migrations_applied:
            return "tests/test_auth.py::test_auth_flow PASSED [100%]\n1 passed in 0.28s"
        else:
            return "tests/test_auth.py::test_auth_flow FAILED (Database table 'auth_users' does not exist)\n1 failed in 0.15s"

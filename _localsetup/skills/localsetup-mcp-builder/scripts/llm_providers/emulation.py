# Purpose: Emulation provider for MCP evaluation (no LLM; JSON-scripted tool calls).
# Created: 2026-02-20
# Last updated: 2026-02-20

"""Emulation provider: runs scripted tool steps from a JSON file and returns predefined response_text. No API keys required."""

import json
import time
from pathlib import Path
from typing import Any


class EmulationProvider:
    """Provider that executes scripted tool steps from JSON and returns predefined response text. Fails the task on first tool error."""

    def __init__(self, script_path: str | Path):
        self.script_path = Path(script_path)
        if not self.script_path.exists() or not self.script_path.is_file():
            raise ValueError(f"Emulation script not found or not a file: {self.script_path}")
        with open(self.script_path, encoding="utf-8", errors="replace") as f:
            data = json.load(f)
        tasks = data.get("tasks")
        if not isinstance(tasks, list):
            raise ValueError(f"Emulation script must have a 'tasks' array; got {type(tasks)}")
        self.tasks = tasks

    def _get_task(self, task_index: int) -> dict[str, Any]:
        if task_index < 0 or task_index >= len(self.tasks):
            raise IndexError(f"Emulation task_index {task_index} out of range [0, {len(self.tasks)})")
        return self.tasks[task_index]

    async def run_agent_loop(
        self,
        question: str,
        tools: list[dict[str, Any]],
        connection: Any,
        task_index: int,
    ) -> tuple[str | None, dict[str, Any]]:
        """Run scripted steps for task_index, then return predefined response_text. Records tool_metrics. Fails on tool error."""
        task = self._get_task(task_index)
        steps = task.get("steps")
        if not isinstance(steps, list):
            steps = []
        response_text = task.get("response_text", "")
        tool_metrics: dict[str, Any] = {}

        for step in steps:
            if not isinstance(step, dict):
                raise ValueError(f"Emulation step must be a dict; got {type(step)}")
            tool_name = step.get("tool")
            arguments = step.get("arguments")
            if not tool_name:
                raise ValueError("Emulation step must have 'tool'")
            if arguments is None:
                arguments = {}
            if not isinstance(arguments, dict):
                raise ValueError(f"Emulation step 'arguments' must be a dict; got {type(arguments)}")

            tool_start_ts = time.time()
            try:
                await connection.call_tool(tool_name, arguments)
            except Exception as e:
                raise RuntimeError(f"Emulation tool call failed: {tool_name}: {e}") from e
            tool_duration = time.time() - tool_start_ts

            if tool_name not in tool_metrics:
                tool_metrics[tool_name] = {"count": 0, "durations": []}
            tool_metrics[tool_name]["count"] += 1
            tool_metrics[tool_name]["durations"].append(tool_duration)

        return response_text, tool_metrics

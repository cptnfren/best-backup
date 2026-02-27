# Purpose: Claude (Anthropic) provider for MCP evaluation harness.
# Created: 2026-02-20
# Last updated: 2026-02-20

"""Claude provider: uses Anthropic SDK for the agent loop. Requires anthropic package and ANTHROPIC_API_KEY."""

import asyncio
import json
import time
import traceback
from typing import Any

EVALUATION_PROMPT = """You are an AI assistant with access to tools.

When given a task, you MUST:
1. Use the available tools to complete the task
2. Provide summary of each step in your approach, wrapped in <summary> tags
3. Provide feedback on the tools provided, wrapped in <feedback> tags
4. Provide your final response, wrapped in <response> tags

Summary Requirements:
- In your <summary> tags, you must explain:
  - The steps you took to complete the task
  - Which tools you used, in what order, and why
  - The inputs you provided to each tool
  - The outputs you received from each tool
  - A summary for how you arrived at the response

Feedback Requirements:
- In your <feedback> tags, provide constructive feedback on the tools:
  - Comment on tool names: Are they clear and descriptive?
  - Comment on input parameters: Are they well-documented? Are required vs optional parameters clear?
  - Comment on descriptions: Do they accurately describe what the tool does?
  - Comment on any errors encountered during tool usage: Did the tool fail to execute? Did the tool return too many tokens?
  - Identify specific areas for improvement and explain WHY they would help
  - Be specific and actionable in your suggestions

Response Requirements:
- Your response should be concise and directly address what was asked
- Always wrap your final response in <response> tags
- If you cannot solve the task return <response>NOT_FOUND</response>
- For numeric responses, provide just the number
- For IDs, provide just the ID
- For names or text, provide the exact text requested
- Your response should go last"""


class ClaudeProvider:
    """Provider that uses Anthropic Claude for the evaluation agent loop."""

    def __init__(self, model: str = "claude-3-7-sonnet-20250219"):
        self.model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            from anthropic import Anthropic
            self._client = Anthropic()
        return self._client

    async def run_agent_loop(
        self,
        question: str,
        tools: list[dict[str, Any]],
        connection: Any,
        task_index: int,
    ) -> tuple[str | None, dict[str, Any]]:
        """Run the agent loop with Claude. task_index is ignored."""
        client = self._get_client()
        messages = [{"role": "user", "content": question}]

        response = await asyncio.to_thread(
            client.messages.create,
            model=self.model,
            max_tokens=4096,
            system=EVALUATION_PROMPT,
            messages=messages,
            tools=tools,
        )

        messages.append({"role": "assistant", "content": response.content})
        tool_metrics: dict[str, Any] = {}

        while response.stop_reason == "tool_use":
            tool_use = next(block for block in response.content if block.type == "tool_use")
            tool_name = tool_use.name
            tool_input = tool_use.input

            tool_start_ts = time.time()
            try:
                tool_result = await connection.call_tool(tool_name, tool_input)
                tool_response = json.dumps(tool_result) if isinstance(tool_result, (dict, list)) else str(tool_result)
            except Exception as e:
                tool_response = f"Error executing tool {tool_name}: {str(e)}\n"
                tool_response += traceback.format_exc()
            tool_duration = time.time() - tool_start_ts

            if tool_name not in tool_metrics:
                tool_metrics[tool_name] = {"count": 0, "durations": []}
            tool_metrics[tool_name]["count"] += 1
            tool_metrics[tool_name]["durations"].append(tool_duration)

            messages.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": tool_response,
                }]
            })

            response = await asyncio.to_thread(
                client.messages.create,
                model=self.model,
                max_tokens=4096,
                system=EVALUATION_PROMPT,
                messages=messages,
                tools=tools,
            )
            messages.append({"role": "assistant", "content": response.content})

        response_text = next(
            (block.text for block in response.content if hasattr(block, "text")),
            None,
        )
        return response_text, tool_metrics

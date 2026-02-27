# Purpose: OpenAI-compatible provider for MCP evaluation (OpenAI and third-party APIs).
# Created: 2026-02-20
# Last updated: 2026-02-20

"""OpenAI-compatible provider: uses openai package with configurable base_url for universal API support."""

import asyncio
import json
import time
import traceback
from typing import Any

# Same system prompt as Claude for consistent evaluation behavior
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


def _mcp_tools_to_openai(mcp_tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert MCP tool list (name, description, input_schema) to OpenAI tools format."""
    result = []
    for t in mcp_tools:
        params = t.get("input_schema")
        if params is None:
            params = {"type": "object", "properties": {}}
        result.append({
            "type": "function",
            "function": {
                "name": t.get("name", "unknown"),
                "description": t.get("description") or "",
                "parameters": params,
            },
        })
    return result


class OpenAICompatibleProvider:
    """Provider that uses OpenAI or any OpenAI-compatible API for the evaluation agent loop."""

    def __init__(
        self,
        model: str = "gpt-4o",
        base_url: str | None = None,
        api_key: str | None = None,
        temperature: float | None = None,
        max_tokens: int = 4096,
    ):
        self.model = model
        self.base_url = base_url
        self.api_key = api_key
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            kwargs = {}
            if self.api_key is not None:
                kwargs["api_key"] = self.api_key
            if self.base_url is not None:
                kwargs["base_url"] = self.base_url
            self._client = OpenAI(**kwargs)
        return self._client

    async def run_agent_loop(
        self,
        question: str,
        tools: list[dict[str, Any]],
        connection: Any,
        task_index: int,
    ) -> tuple[str | None, dict[str, Any]]:
        """Run the agent loop with OpenAI-compatible API. task_index is ignored."""
        client = self._get_client()
        openai_tools = _mcp_tools_to_openai(tools)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": EVALUATION_PROMPT},
            {"role": "user", "content": question},
        ]
        tool_metrics: dict[str, Any] = {}

        def _create(messages_arg: list) -> Any:
            kwargs: dict[str, Any] = {
                "model": self.model,
                "messages": messages_arg,
                "tools": openai_tools,
                "max_tokens": self.max_tokens,
            }
            if self.temperature is not None:
                kwargs["temperature"] = self.temperature
            return client.chat.completions.create(**kwargs)

        def _assistant_msg(m: Any) -> dict[str, Any]:
            out = {"role": "assistant", "content": m.content or ""}
            if getattr(m, "tool_calls", None):
                out["tool_calls"] = [
                    {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments or "{}"}}
                    for tc in m.tool_calls
                ]
            return out

        response = await asyncio.to_thread(_create, messages)
        choice = response.choices[0]
        msg = choice.message
        messages.append(_assistant_msg(msg))

        while getattr(choice, "finish_reason", None) == "tool_calls" and getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls:
                tool_id = tc.id
                fn = tc.function
                tool_name = fn.name
                try:
                    arguments = json.loads(fn.arguments) if fn.arguments else {}
                except (json.JSONDecodeError, TypeError) as e:
                    raise ValueError(f"OpenAI provider: invalid tool arguments JSON for {tool_name}: {e}") from e

                tool_start_ts = time.time()
                try:
                    tool_result = await connection.call_tool(tool_name, arguments)
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
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": tool_response,
                })

            response = await asyncio.to_thread(_create, messages)
            choice = response.choices[0]
            msg = choice.message
            messages.append(_assistant_msg(msg))

        response_text = msg.content
        return response_text, tool_metrics

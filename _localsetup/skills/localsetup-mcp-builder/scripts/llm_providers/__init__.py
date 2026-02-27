# Purpose: Pluggable LLM providers for MCP evaluation (Claude, OpenAI-compatible, emulation).
# Created: 2026-02-20
# Last updated: 2026-02-20

"""LLM provider interface and factory. Import provider implementations lazily to avoid loading SDKs at startup."""

from typing import Any, Protocol


class LLMProvider(Protocol):
    """Protocol for evaluation providers: run one agent loop and return response text + tool metrics."""

    async def run_agent_loop(
        self,
        question: str,
        tools: list[dict[str, Any]],
        connection: Any,
        task_index: int,
    ) -> tuple[str | None, dict[str, Any]]:
        """Run the agent loop for one task. Returns (response_text, tool_metrics)."""
        ...


def create_provider(
    provider_name: str,
    *,
    model: str | None = None,
    openai_base_url: str | None = None,
    openai_api_key: str | None = None,
    openai_temperature: float | None = None,
    openai_max_tokens: int | None = None,
    emulation_script_path: str | None = None,
) -> LLMProvider:
    """Create the requested provider. Lazy-imports provider modules."""
    if provider_name == "claude":
        from .claude import ClaudeProvider
        return ClaudeProvider(model=model or "claude-3-7-sonnet-20250219")
    if provider_name == "openai":
        from .openai_compat import OpenAICompatibleProvider
        return OpenAICompatibleProvider(
            model=model or "gpt-4o",
            base_url=openai_base_url,
            api_key=openai_api_key,
            temperature=openai_temperature,
            max_tokens=openai_max_tokens or 4096,
        )
    if provider_name == "emulation":
        from .emulation import EmulationProvider
        if not emulation_script_path:
            raise ValueError("emulation_script_path is required for provider=emulation")
        return EmulationProvider(script_path=emulation_script_path)
    raise ValueError(f"Unknown provider: {provider_name}. Use claude, openai, or emulation.")

"""MCP Server Evaluation Harness

Evaluates MCP servers by running test questions against them. Supports three
providers: Claude (Anthropic), OpenAI-compatible APIs, and emulation (JSON-scripted, no LLM).
"""

import argparse
import asyncio
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

# No top-level imports of anthropic, openai, or connections so that --help and emulation
# can run without loading those dependencies. Provider and connection are created in main().


def parse_evaluation_file(file_path: Path) -> list[dict[str, Any]]:
    """Parse XML evaluation file with qa_pair elements."""
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        evaluations = []

        for qa_pair in root.findall(".//qa_pair"):
            question_elem = qa_pair.find("question")
            answer_elem = qa_pair.find("answer")

            if question_elem is not None and answer_elem is not None:
                evaluations.append({
                    "question": (question_elem.text or "").strip(),
                    "answer": (answer_elem.text or "").strip(),
                })

        return evaluations
    except Exception as e:
        print(f"Error parsing evaluation file {file_path}: {e}")
        return []


def extract_xml_content(text: str | None, tag: str) -> str | None:
    """Extract content from XML tags."""
    if not text:
        return None
    pattern = rf"<{tag}>(.*?)</{tag}>"
    matches = re.findall(pattern, text, re.DOTALL)
    return matches[-1].strip() if matches else None


async def evaluate_single_task(
    provider: Any,
    qa_pair: dict[str, Any],
    tools: list[dict[str, Any]],
    connection: Any,
    task_index: int,
) -> dict[str, Any]:
    """Evaluate a single QA pair using the given provider."""
    import time
    start_time = time.time()

    print(f"Task {task_index + 1}: Running task with question: {qa_pair['question']}")
    try:
        response, tool_metrics = await provider.run_agent_loop(
            qa_pair["question"], tools, connection, task_index
        )
    except Exception as e:
        duration_seconds = time.time() - start_time
        return {
            "question": qa_pair["question"],
            "expected": qa_pair["answer"],
            "actual": None,
            "score": 0,
            "total_duration": duration_seconds,
            "tool_calls": {},
            "num_tool_calls": 0,
            "summary": f"Provider error: {e}",
            "feedback": "",
        }

    response_value = extract_xml_content(response, "response")
    summary = extract_xml_content(response, "summary")
    feedback = extract_xml_content(response, "feedback")
    duration_seconds = time.time() - start_time

    return {
        "question": qa_pair["question"],
        "expected": qa_pair["answer"],
        "actual": response_value,
        "score": int(response_value == qa_pair["answer"]) if response_value else 0,
        "total_duration": duration_seconds,
        "tool_calls": tool_metrics,
        "num_tool_calls": sum(len(m.get("durations", [])) for m in tool_metrics.values()),
        "summary": summary,
        "feedback": feedback,
    }


REPORT_HEADER = """
# Evaluation Report

## Summary

- **Accuracy**: {correct}/{total} ({accuracy:.1f}%)
- **Average Task Duration**: {average_duration_s:.2f}s
- **Average Tool Calls per Task**: {average_tool_calls:.2f}
- **Total Tool Calls**: {total_tool_calls}

---
"""

TASK_TEMPLATE = """
### Task {task_num}

**Question**: {question}
**Ground Truth Answer**: `{expected_answer}`
**Actual Answer**: `{actual_answer}`
**Correct**: {correct_indicator}
**Duration**: {total_duration:.2f}s
**Tool Calls**: {tool_calls}

**Summary**
{summary}

**Feedback**
{feedback}

---
"""


async def run_evaluation(
    eval_path: Path,
    connection: Any,
    provider: Any,
) -> str:
    """Run evaluation with MCP server tools and the given provider."""
    print("Starting Evaluation")

    tools = await connection.list_tools()
    print(f"Loaded {len(tools)} tools from MCP server")

    qa_pairs = parse_evaluation_file(eval_path)
    print(f"Loaded {len(qa_pairs)} evaluation tasks")

    # Emulation: validate task count alignment (Gap 3)
    if hasattr(provider, "tasks"):
        if len(provider.tasks) != len(qa_pairs):
            msg = (
                f"Emulation script has {len(provider.tasks)} tasks but evaluation file has {len(qa_pairs)} qa_pairs; counts must match."
            )
            print(msg, file=sys.stderr)
            raise ValueError(msg)

    results = []
    for i, qa_pair in enumerate(qa_pairs):
        print(f"Processing task {i + 1}/{len(qa_pairs)}")
        result = await evaluate_single_task(provider, qa_pair, tools, connection, i)
        results.append(result)

    correct = sum(r["score"] for r in results)
    accuracy = (correct / len(results)) * 100 if results else 0
    average_duration_s = sum(r["total_duration"] for r in results) / len(results) if results else 0
    average_tool_calls = sum(r["num_tool_calls"] for r in results) / len(results) if results else 0
    total_tool_calls = sum(r["num_tool_calls"] for r in results)

    report = REPORT_HEADER.format(
        correct=correct,
        total=len(results),
        accuracy=accuracy,
        average_duration_s=average_duration_s,
        average_tool_calls=average_tool_calls,
        total_tool_calls=total_tool_calls,
    )

    report += "".join([
        TASK_TEMPLATE.format(
            task_num=i + 1,
            question=qa_pair["question"],
            expected_answer=qa_pair["answer"],
            actual_answer=result["actual"] or "N/A",
            correct_indicator="[OK]" if result["score"] else "[FAIL]",
            total_duration=result["total_duration"],
            tool_calls=json.dumps(result["tool_calls"], indent=2),
            summary=result["summary"] or "N/A",
            feedback=result["feedback"] or "N/A",
        )
        for i, (qa_pair, result) in enumerate(zip(qa_pairs, results))
    ])

    return report


def parse_headers(header_list: list[str] | None) -> dict[str, str]:
    """Parse header strings in format 'Key: Value' into a dictionary."""
    headers = {}
    if not header_list:
        return headers
    for header in header_list:
        if ":" in header:
            key, value = header.split(":", 1)
            headers[key.strip()] = value.strip()
        else:
            print(f"Warning: Ignoring malformed header: {header}")
    return headers


def parse_env_vars(env_list: list[str] | None) -> dict[str, str]:
    """Parse environment variable strings in format 'KEY=VALUE' into a dictionary."""
    env = {}
    if not env_list:
        return env
    for env_var in env_list:
        if "=" in env_var:
            key, value = env_var.split("=", 1)
            env[key.strip()] = value.strip()
        else:
            print(f"Warning: Ignoring malformed environment variable: {env_var}")
    return env


async def main():
    parser = argparse.ArgumentParser(
        description="Evaluate MCP servers using test questions (Claude, OpenAI-compatible, or emulation)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Claude (default)
  python evaluation.py -t stdio -c python -a my_server.py eval.xml

  # OpenAI-compatible (e.g. OpenAI or third-party API)
  python evaluation.py --provider openai -t stdio -c python -a my_server.py eval.xml

  # Emulation (no API keys; JSON script drives tool calls)
  python evaluation.py --provider emulation --emulation-script emulation.json -t stdio -c python -a my_server.py eval.xml
        """,
    )
    parser.add_argument("eval_file", type=Path, help="Path to evaluation XML file")
    parser.add_argument(
        "--provider",
        choices=["claude", "openai", "emulation"],
        default="claude",
        help="LLM provider: claude, openai, or emulation (default: claude)",
    )
    parser.add_argument("-m", "--model", help="Model name (default depends on provider)")
    parser.add_argument("-t", "--transport", choices=["stdio", "sse", "http"], default="stdio", help="MCP transport (default: stdio)")
    stdio_group = parser.add_argument_group("stdio options")
    stdio_group.add_argument("-c", "--command", help="Command to run MCP server (stdio only)")
    stdio_group.add_argument("-a", "--args", nargs="+", help="Arguments for the command (stdio only)")
    stdio_group.add_argument("-e", "--env", nargs="+", help="Environment variables in KEY=VALUE format (stdio only)")
    remote_group = parser.add_argument_group("sse/http options")
    remote_group.add_argument("-u", "--url", help="MCP server URL (sse/http only)")
    remote_group.add_argument("-H", "--header", nargs="+", dest="headers", help="HTTP headers in 'Key: Value' format (sse/http only)")
    parser.add_argument("--emulation-script", type=Path, help="Path to emulation JSON script (required when provider=emulation)")
    parser.add_argument("--openai-base-url", help="OpenAI-compatible API base URL (optional)")
    parser.add_argument("--openai-api-key", help="OpenAI API key (or set OPENAI_API_KEY)")
    parser.add_argument("--temperature", type=float, help="Temperature (OpenAI provider)")
    parser.add_argument("--max-tokens", type=int, default=4096, help="Max tokens (default: 4096)")
    parser.add_argument("-o", "--output", type=Path, help="Output file for evaluation report (default: stdout)")

    args = parser.parse_args()

    # Input hardening
    eval_path = args.eval_file.resolve()
    if not eval_path.exists() or not eval_path.is_file():
        print(f"Error: Evaluation file not found: {args.eval_file}", file=sys.stderr)
        sys.exit(1)
    if args.url and len(args.url) > 2048:
        print("Error: URL length exceeds 2048", file=sys.stderr)
        sys.exit(2)
    if args.provider == "emulation" and not args.emulation_script:
        print("Error: --emulation-script is required when --provider emulation", file=sys.stderr)
        sys.exit(1)

    # Create provider (lazy-loads provider modules)
    try:
        from llm_providers import create_provider  # noqa: PLC0415
        provider = create_provider(
            args.provider,
            model=args.model,
            openai_base_url=args.openai_base_url,
            openai_api_key=args.openai_api_key or __import__("os").environ.get("OPENAI_API_KEY"),
            openai_temperature=args.temperature,
            openai_max_tokens=args.max_tokens,
            emulation_script_path=str(args.emulation_script.resolve()) if args.emulation_script else None,
        )
    except Exception as e:
        print(f"Error creating provider: {e}", file=sys.stderr)
        sys.exit(1)

    # Build MCP connection (lazy import so --help does not load mcp)
    headers = parse_headers(args.headers) if args.headers else None
    env_vars = parse_env_vars(args.env) if args.env else None
    try:
        from connections import create_connection
        connection = create_connection(
            transport=args.transport,
            command=args.command,
            args=args.args,
            env=env_vars,
            url=args.url,
            headers=headers,
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Connecting to MCP server via {args.transport}...", file=sys.stderr)

    async with connection:
        print("Connected successfully", file=sys.stderr)
        report = await run_evaluation(eval_path, connection, provider)

        if args.output:
            args.output.write_text(report, encoding="utf-8", errors="replace")
            print(f"\nReport saved to {args.output}", file=sys.stderr)
        else:
            print("\n" + report)


if __name__ == "__main__":
    asyncio.run(main())

"""Verify whether AI sessions used nexo MCP tools correctly."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_DEFAULT_SESSION_LOG = Path.home() / ".nexo_session.jsonl"

_REQUIRED_TOOLS = {
    "graph_summary": ("graph_summary",),
    "resolve_nodes": ("resolve_nodes",),
    "explain_node": ("explain_node", "explainnode"),
    "shortest_path": ("shortest_path", "shortestpath"),
    "expand_subgraph": ("expand_subgraph", "expandsubgraph"),
    "workspace_query": ("workspace_query", "workspacequery"),
}


def _parse_ts(value: str) -> datetime | None:
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _load_session_entries(session_log: Path) -> list[dict[str, Any]]:
    if not session_log.exists():
        return []

    rows: list[dict[str, Any]] = []
    for line in session_log.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _tool_kind(tool_name: str) -> str | None:
    t = (tool_name or "").lower()
    if "nexo" not in t:
        return None

    for canonical, aliases in _REQUIRED_TOOLS.items():
        if any(alias in t for alias in aliases):
            return canonical
    return None


def verify_mcp_usage(
    *,
    workspace: Path,
    session_log: Path | None = None,
    window_hours: int = 24,
    mode: str = "strict",
    min_calls: int = 2,
) -> dict[str, Any]:
    if mode not in {"basic", "strict"}:
        raise ValueError("mode must be 'basic' or 'strict'")
    if window_hours <= 0:
        raise ValueError("window_hours must be positive")
    if min_calls <= 0:
        raise ValueError("min_calls must be positive")

    log_path = session_log or _DEFAULT_SESSION_LOG
    rows = _load_session_entries(log_path)
    now = datetime.now(timezone.utc)
    lower_bound = now - timedelta(hours=window_hours)
    workspace_resolved = workspace.resolve()

    filtered: list[dict[str, Any]] = []
    for row in rows:
        ts = _parse_ts(str(row.get("ts", "")))
        if not ts:
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        if ts < lower_bound:
            continue

        raw_workspace = str(row.get("workspace", "")).strip()
        if raw_workspace:
            try:
                row_workspace = Path(raw_workspace).resolve()
                in_workspace = (
                    row_workspace == workspace_resolved
                    or workspace_resolved in row_workspace.parents
                    or row_workspace in workspace_resolved.parents
                )
                if not in_workspace:
                    continue
            except Exception:
                continue
        else:
            continue

        filtered.append(row)

    tool_counts: Counter[str] = Counter()
    unknown_nexo_tools: Counter[str] = Counter()
    for row in filtered:
        tool_name = str(row.get("tool", ""))
        kind = _tool_kind(tool_name)
        if kind:
            tool_counts[kind] += 1
        elif "nexo" in tool_name.lower():
            unknown_nexo_tools[tool_name] += 1

    mcp_calls = sum(tool_counts.values())
    passed = True
    missing: list[str] = []

    if mcp_calls < min_calls:
        passed = False
        missing.append(f"at least {min_calls} nexo MCP tool calls")

    if mode == "strict":
        if tool_counts["graph_summary"] == 0:
            passed = False
            missing.append("graph_summary call")
        deep_tools = (
            tool_counts["resolve_nodes"]
            + tool_counts["explain_node"]
            + tool_counts["shortest_path"]
            + tool_counts["expand_subgraph"]
            + tool_counts["workspace_query"]
        )
        if deep_tools == 0:
            passed = False
            missing.append(
                "at least one targeted query call (resolve_nodes/explain_node/shortest_path/expand_subgraph/workspace_query)"
            )

    status = "PASS" if passed else "FAIL"
    summary_lines = [
        f"[{status}] nexo MCP verification",
        f"  workspace: {workspace_resolved}",
        f"  session log: {log_path}",
        f"  window: last {window_hours}h",
        f"  mode: {mode}",
        f"  nexo MCP calls: {mcp_calls}",
    ]

    if tool_counts:
        summary_lines.append("  tool usage:")
        for tool_name in sorted(_REQUIRED_TOOLS.keys()):
            summary_lines.append(f"    - {tool_name}: {tool_counts.get(tool_name, 0)}")

    if unknown_nexo_tools:
        summary_lines.append("  unclassified nexo-like tools:")
        for name, count in unknown_nexo_tools.items():
            summary_lines.append(f"    - {name}: {count}")

    if missing:
        summary_lines.append("  missing requirements:")
        for item in missing:
            summary_lines.append(f"    - {item}")

    if not filtered:
        summary_lines.append("  note: no matching session entries found for this workspace/time window")

    return {
        "pass": passed,
        "mode": mode,
        "workspace": str(workspace_resolved),
        "session_log": str(log_path),
        "window_hours": window_hours,
        "min_calls": min_calls,
        "entries_considered": len(filtered),
        "mcp_calls": mcp_calls,
        "tool_counts": dict(tool_counts),
        "unknown_nexo_tools": dict(unknown_nexo_tools),
        "missing": missing,
        "text": "\n".join(summary_lines),
    }

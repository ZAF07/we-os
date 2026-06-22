"""Memory tools for agents.

Two complementary mechanisms:

- **In-task sharing** is handled natively by ADK session state (`output_key` +
  `{key}` templating), so no tool is needed for a downstream sub-agent to read an
  upstream one's deliverable.
- **Cross-task recall** uses the wired `MemoryService`: `recall` searches past
  campaigns; `remember` jots a durable note into session state that the
  orchestrator persists to memory at the end of the run.

`recall` is async because `ToolContext.search_memory` is async.
"""

from __future__ import annotations

from google.adk.tools import ToolContext


async def recall(query: str, tool_context: ToolContext) -> dict:
    """Search long-term memory (past campaigns/sessions) for relevant context.

    Args:
        query: What to look up (e.g. "prior coffee campaigns positioning").
        tool_context: Injected by ADK; provides access to the MemoryService.

    Returns:
        {results: [text, ...]} — snippets from prior sessions, possibly empty.
    """
    try:
        response = await tool_context.search_memory(query)
    except Exception as exc:  # memory service optional / not wired
        return {"results": [], "note": f"memory unavailable: {exc}"}
    results: list[str] = []
    for entry in getattr(response, "memories", []) or []:
        content = getattr(entry, "content", None)
        for part in getattr(content, "parts", []) or []:
            if getattr(part, "text", None):
                results.append(part.text)
    return {"results": results}


def remember(note: str, tool_context: ToolContext) -> dict:
    """Record a durable note for downstream agents and future-task retrieval.

    The note is appended to session state under ``notes``; the orchestrator
    persists the whole session to long-term memory when the run completes.

    Args:
        note: A concise, self-contained fact worth keeping.
        tool_context: Injected by ADK; gives access to mutable session state.

    Returns:
        {ok: True, count: <notes so far>}.
    """
    notes = list(tool_context.state.get("notes", []))
    notes.append(note)
    tool_context.state["notes"] = notes
    return {"ok": True, "count": len(notes)}

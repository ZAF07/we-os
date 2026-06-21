"""A specialist agent = AgentSpec + provider + allowed tools + an agent loop.

Composes the effective system prompt (governance preamble + Customer DNA + the
agent's own body) and drives a conversation via the configured `AgentLoop`.
Supports `resume()` so the QA self-critique loop can hand the agent revision
instructions on the same conversation, preserving its context.
"""

from __future__ import annotations

from typing import Optional

from ..loop import AgentLoop, DefaultToolUseLoop, LoopContext, LoopResult
from ..providers.base import Provider
from ..tools import FilesystemSandbox, build_registry
from ..types import Message
from .loader import AgentSpec


def compose_system(governance: str, dna_text: str, agent_body: str) -> str:
    """Assemble the system prompt the specialist runs under."""
    return (
        f"{governance}\n\n"
        "# Customer DNA (ground every recommendation in this; never invent what it omits)\n\n"
        f"{dna_text}\n\n"
        "# Your role and guardrails\n\n"
        f"{agent_body}"
    )


class Specialist:
    """Runs one specialist agent over an agent loop, with QA-friendly resume()."""

    def __init__(
        self,
        spec: AgentSpec,
        *,
        provider: Provider,
        sandbox: FilesystemSandbox,
        governance: str,
        dna_text: str,
        web_backend=None,
        loop: Optional[AgentLoop] = None,
        max_steps: int = 20,
        max_tokens: int = 16000,
        stream: bool = True,
    ) -> None:
        self.spec = spec
        self.provider = provider
        self.registry = build_registry(spec.tools, sandbox=sandbox, web_backend=web_backend)
        self.loop = loop or DefaultToolUseLoop()
        self.system = compose_system(governance, dna_text, spec.body)
        self.max_steps = max_steps
        self.max_tokens = max_tokens
        self.stream = stream

    def _run(self, history: list[Message]) -> LoopResult:
        ctx = LoopContext(
            provider=self.provider,
            system=self.system,
            history=history,
            tools=self.registry,
            max_steps=self.max_steps,
            max_tokens=self.max_tokens,
            stream=self.stream,
        )
        return self.loop.run(ctx)

    def start(self, task: str) -> LoopResult:
        """Begin a fresh conversation with the given task brief."""
        return self._run([Message.user(task)])

    def resume(self, history: list[Message], instruction: str) -> LoopResult:
        """Continue the conversation with a revision instruction (used by QA)."""
        return self._run(list(history) + [Message.user(instruction)])

"""The provider adapter interface (the seam that makes the harness agnostic).

Every LLM backend is wrapped by a `Provider` subclass that translates between
the harness's normalized `Message`/`ToolCall`/`CompletionResult` types and the
backend's own SDK shapes. Code above this layer (the agent loop, specialists,
orchestrator) never imports a vendor SDK or touches a vendor-specific field.

Tool schemas are passed to `complete()` as a list of plain dicts in this
normalized shape (the adapter converts to its own wire format):

    {"name": str, "description": str, "parameters": <JSON Schema dict>}
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, Optional

from ..config import ProviderConfig
from ..types import CompletionResult, Message

ToolSchema = dict  # {"name", "description", "parameters"}
OnText = Callable[[str], None]


class Provider(ABC):
    """Adapter interface implemented by every backend (DeepSeek, Claude, OpenAI…)."""

    #: Stable adapter name, also used as the `provider` tag on assistant messages.
    name: str = "base"

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    @abstractmethod
    def complete(
        self,
        *,
        system: Optional[str],
        messages: list[Message],
        tools: Optional[list[ToolSchema]] = None,
        max_tokens: int = 16000,
        stream: bool = True,
        on_text: Optional[OnText] = None,
    ) -> CompletionResult:
        """Run one model turn.

        Args:
            system: System prompt (governance preamble + DNA + agent body).
            messages: Full normalized conversation history.
            tools: Normalized tool schemas the model may call (or None).
            max_tokens: Hard output ceiling for this turn.
            stream: If True, stream tokens and invoke `on_text` with each text delta.
            on_text: Callback for streamed text deltas (UI/logging); may be None.

        Returns:
            A CompletionResult whose `assistant_message` is ready to append to
            history verbatim (preserving any provider-native content for replay).
        """
        raise NotImplementedError

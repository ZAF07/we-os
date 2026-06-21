"""DefaultToolUseLoop — a complete, working reference implementation.

The standard agentic tool-use loop: ask the model, and while it requests tools,
dispatch them and feed the results back, until it stops asking (or we hit
`max_steps`). It uses the seams defined on `AgentLoop`, so you can subclass it
and override just one method (e.g. `should_continue`) without rewriting the body.

This is what specialists use out of the box. Replace it by passing a different
`AgentLoop` into `Specialist`.
"""

from __future__ import annotations

from ..errors import GuardrailError
from ..types import Message
from .base import AgentLoop, LoopContext, LoopResult


class DefaultToolUseLoop(AgentLoop):
    """Reference loop: model -> (tool_use -> dispatch -> feed back)* -> end_turn."""

    def run(self, ctx: LoopContext) -> LoopResult:
        final_text = ""
        while True:
            ctx.step += 1
            self.hooks.before_step(ctx)

            result = self.model_turn(ctx)
            self.hooks.on_assistant_message(ctx, result)
            ctx.history.append(result.assistant_message)
            final_text = result.text

            if result.stop_reason == "refusal":
                # Surface refusals explicitly rather than treating empty text as success.
                raise GuardrailError(
                    "The model refused to produce this deliverable (stop_reason=refusal)."
                )

            if not self.should_continue(ctx, result):
                break

            # Dispatch every requested tool, append one tool-result message each.
            for call in result.tool_calls:
                tool_result = self.execute_tool(ctx, call)
                ctx.history.append(Message.from_tool_result(tool_result, name=call.name))

        loop_result = LoopResult(
            final_text=final_text,
            history=ctx.history,
            usage=ctx.usage,
            steps=ctx.step,
            stop_reason=ctx.last_stop_reason,
        )
        self.on_finish(ctx, loop_result)
        return loop_result

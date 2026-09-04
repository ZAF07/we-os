import { describe, expect, it } from "vitest";

import { EngineError } from "@/lib/engine-error";
import { refusalMessage } from "@/lib/refusal";

/**
 * Builds an engine failure as the API returns one.
 *
 * Args:
 *   status: The HTTP status.
 *   detail: The error body, which carries the type and any extra fields.
 *
 * Returns:
 *   The typed error the frontend receives.
 */
function refusal(status: number, detail: Record<string, unknown>): EngineError {
  return new EngineError(status, detail);
}

describe("refusalMessage", () => {
  it("appends how far past the allowance the business is", () => {
    const message = refusalMessage(
      refusal(402, {
        type: "quota_exhausted",
        message: "Your allowance is used up.",
        used: 1042.5,
        allowance: 1000,
      }),
    );

    expect(message).toContain("Your allowance is used up.");
    expect(message).toContain("1042.50");
    expect(message).toContain("1000.00");
  });

  it("falls back to the engine's words when the numbers are missing", () => {
    const message = refusalMessage(
      refusal(402, {
        type: "quota_exhausted",
        message: "Your allowance is used up.",
      }),
    );

    expect(message).toBe("Your allowance is used up.");
  });

  it("names the fields a failed gate is still owed", () => {
    const message = refusalMessage(
      refusal(409, {
        type: "gate_failed",
        message: "Stage 0 gate failed",
        missing_fields: ["Business name", "Price point"],
      }),
    );

    expect(message).toBe(
      "Stage 0 gate failed Still needed: Business name; Price point",
    );
  });

  it("reads a quota refusal as quota even when it also names fields", () => {
    // Keyed on the error's own type, not on which field happens to be present:
    // a refusal carrying both would otherwise be reported as a gate failure and
    // send the person to fix a Brand DNA that is already complete.
    const message = refusalMessage(
      refusal(402, {
        type: "quota_exhausted",
        message: "Your allowance is used up.",
        used: 1000,
        allowance: 1000,
        missing_fields: ["Business name"],
      }),
    );

    expect(message).toContain("You have used");
    expect(message).not.toContain("Still needed");
  });

  it("passes through a refusal that carries no extra detail", () => {
    const message = refusalMessage(
      refusal(409, {
        type: "run_conflict",
        message: "This campaign is already being run.",
      }),
    );

    expect(message).toBe("This campaign is already being run.");
  });

  it("rethrows anything that is not an engine failure, since that is a fault", () => {
    expect(() => refusalMessage(new TypeError("boom"))).toThrow(TypeError);
  });
});

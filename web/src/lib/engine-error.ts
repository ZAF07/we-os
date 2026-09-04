/**
 * The engine's typed failure, separate from the client that raises it.
 *
 * Kept out of `engine.ts` because that module is `server-only`: the message a
 * screen builds from a refusal is pure logic worth testing, and it should not
 * have to cross the server boundary to be reachable.
 */

/** A typed error mirroring the engine's `Error` schema from the frozen contract. */
export class EngineError extends Error {
  readonly status: number;
  readonly type: string;
  readonly detail: Record<string, unknown>;

  constructor(status: number, detail: Record<string, unknown>) {
    super(String(detail.message ?? `Engine request failed (${status})`));
    this.name = "EngineError";
    this.status = status;
    this.type = String(detail.type ?? "internal");
    this.detail = detail;
  }
}

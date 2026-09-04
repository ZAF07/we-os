import { engineStream } from "@/lib/engine";

export const dynamic = "force-dynamic";

/**
 * Attaches to one run's live progress stream, proxying it to the browser.
 *
 * The browser never calls the engine directly — the BFF holds the session and
 * forwards the verified token (ADR-0012, ADR-0013) — but a stream cannot be
 * read through a server action, which returns once. So live run progress
 * reaches the page through this route: it attaches through the engine adapter
 * and pipes the frames straight back, adding nothing.
 *
 * Args:
 *   request: The incoming request, whose abort signal closes the upstream
 *     stream when the reader goes away.
 *   context: The route params carrying the run id.
 *
 * Returns:
 *   The engine's event stream, or its status when the run is not the caller's.
 */
export async function GET(
  request: Request,
  context: { params: Promise<{ runId: string }> },
): Promise<Response> {
  const { runId } = await context.params;
  const upstream = await engineStream(
    `/runs/${encodeURIComponent(runId)}/stream`,
    request.signal,
  );

  if (!upstream.ok || upstream.body === null) {
    return new Response(null, { status: upstream.status });
  }

  return new Response(upstream.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  });
}

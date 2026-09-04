import { auth } from "@clerk/nextjs/server";

/**
 * Proxies a run's Server-Sent Events stream from the engine to the browser.
 *
 * The browser never calls the engine directly — the BFF holds the session and
 * forwards the verified token (ADR-0012, ADR-0013) — but a stream cannot be
 * read through a server action, which returns once. So live run progress
 * reaches the page through this route: it attaches to the engine's stream and
 * pipes the frames straight back, adding nothing.
 */

const ENGINE_BASE_URL = process.env.ENGINE_BASE_URL ?? "http://127.0.0.1:8000";

export const dynamic = "force-dynamic";

/**
 * Attaches to one run's live progress stream.
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
  const { getToken } = await auth();
  const token = await getToken();

  const upstream = await fetch(
    `${ENGINE_BASE_URL}/runs/${encodeURIComponent(runId)}/stream`,
    {
      cache: "no-store",
      signal: request.signal,
      headers: {
        Accept: "text/event-stream",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    },
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

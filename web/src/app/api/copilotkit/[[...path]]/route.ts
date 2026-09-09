import { CopilotRuntime, createCopilotRuntimeHandler } from "@copilotkit/runtime/v2";
import { HttpAgent } from "@ag-ui/client";

/**
 * The CopilotKit runtime, on the v2 API.
 *
 * This process still calls no model. The runtime relays the browser to the
 * AG-UI endpoint api.py mounts, and the ADK agent behind it does the model
 * work - which is why v2 is a simplification here rather than a rewrite:
 * v1 required a `serviceAdapter`, and the only honest one for a relay was
 * `ExperimentalEmptyAdapter`, a placeholder for the LLM call that never
 * happens. v2 drops the concept, so the wiring now says what it does.
 *
 * The catch-all segment is load-bearing. v2's handler is multi-route - it
 * serves POST /agent/:agentId/run, GET /info and siblings beneath the base
 * path - so a single `route.ts` at /api/copilotkit would answer the base
 * path and 404 everything under it. That was already visible on v1 as a
 * GET /api/copilotkit/info 404 on every page load; the catch-all is what
 * actually fixes it, rather than the GET re-export that used to paper over
 * it by answering the wrong URL. Both are now observed serving 200.
 *
 * `createCopilotRuntimeHandler` returns a plain (Request) => Response, so
 * no Hono or Express adapter is needed - which matters because `hono` is
 * not a dependency of this project and the v2 docs' Hono example would
 * have pulled one in for nothing.
 */

// Server-side, so this can be a private origin in production. It falls
// back to NEXT_PUBLIC_API_BASE because in this deployment both point at
// the same FastAPI service; on Cloud Run the two can differ, with the
// frontend reaching the API over the internal URL.
const apiBase =
  process.env.API_BASE_INTERNAL ??
  process.env.NEXT_PUBLIC_API_BASE ??
  "http://localhost:8000";

const runtime = new CopilotRuntime({
  agents: {
    // Key must match the `agentId` the chat component asks for.
    mechnari: new HttpAgent({ url: `${apiBase}/api/ag-ui` }),
  },
});

const handler = createCopilotRuntimeHandler({
  runtime,
  // Strict prefix stripping rather than suffix matching, so the routes are
  // resolved against a known mount point instead of whatever the URL
  // happens to end with.
  basePath: "/api/copilotkit",
});

export const POST = (request: Request) => handler(request);
export const GET = (request: Request) => handler(request);

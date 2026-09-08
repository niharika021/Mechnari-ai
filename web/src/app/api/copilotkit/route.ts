import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { HttpAgent } from "@ag-ui/client";
import { NextRequest } from "next/server";

// The CopilotKit runtime proxies the browser to the AG-UI endpoint that
// api.py mounts. The empty service adapter is correct here on purpose:
// there is no LLM call in this process at all - the ADK agent behind
// AG-UI does the model work, and this route only relays its event stream.
const serviceAdapter = new ExperimentalEmptyAdapter();

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
    // Name must match the `agent` prop on <CopilotKit> in layout.tsx.
    mechnari: new HttpAgent({ url: `${apiBase}/api/ag-ui` }),
  },
});

const handler = async (req: NextRequest) => {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilotkit",
  });
  return handleRequest(req);
};

export const POST = handler;

// The client probes GET /api/copilotkit/info to decide whether the runtime
// is reachable; without a GET export that 404s and the console logs a
// "no-answer" reachability failure on every load, even though chat itself
// works over POST.
export const GET = handler;

"use client";

import type { ReactNode } from "react";
import { CopilotKit } from "@copilotkit/react-core";

/**
 * Client wrapper around CopilotKit's provider.
 *
 * No onError handler here on purpose. It was tried and removed: CopilotKit
 * only routes its own client-side error classes through onError, and an
 * AG-UI RUN_ERROR from the agent never reaches it (verified by logging
 * every event the handler received while the backend returned a 401 - the
 * handler was not called at all). Surfacing a failed copilot is therefore
 * done by asking the API whether the key actually authenticates, in
 * MechnariCopilot, rather than by waiting for an event that will not come.
 */
export function CopilotProvider({ children }: { children: ReactNode }) {
  return (
    <CopilotKit
      runtimeUrl="/api/copilotkit"
      agent="mechnari"
      // CopilotKit's dev console overlays a debug button in the corner -
      // useful while developing, noise in a demo.
      showDevConsole={false}
    >
      {children}
    </CopilotKit>
  );
}

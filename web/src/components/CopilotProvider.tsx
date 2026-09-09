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
      // Since 1.70 there is a second, separate debug surface: the web
      // inspector, which showDevConsole does not gate. It opens a large
      // panel over the middle of the page - directly on top of the intake
      // form the copilot is filling in, which is the one thing a viewer
      // needs to be able to see. It is development-only and can never
      // render in production, so this changes nothing about the deployed
      // site; it is here so the local run looks like the deployed one.
      enableInspector={false}
    >
      {children}
    </CopilotKit>
  );
}

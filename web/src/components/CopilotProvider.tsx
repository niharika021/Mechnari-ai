"use client";

import type { ReactNode } from "react";
import { CopilotKitProvider } from "@copilotkit/react-core/v2";

/**
 * Client wrapper around CopilotKit's provider, on the v2 API.
 *
 * No onError handler here. On v1 one was tried and removed: CopilotKit
 * routed only its own client-side error classes through onError, and an
 * AG-UI RUN_ERROR from the agent never reached it (verified by logging
 * every event the handler received while the backend returned a 401 - the
 * handler was not called at all). v2's types claim broader coverage -
 * "Fires for all error types (runtime connection failures, agent errors,
 * tool errors)" - and an agent run error does now reach CopilotKit's own
 * logger, which it did not before. Whether it reaches a provider-level
 * onError has not been tested here, so this stays absent rather than
 * added on the strength of a docstring.
 *
 * It would not replace the health check either way. MechnariCopilot asks
 * the API whether the credential actually authenticates, which warns
 * before the engineer types their first question; onError can only report
 * after a message has already failed.
 *
 * There is no `agent` prop in v2 - which agent to talk to is now the
 * chat component's business (`agentId`), not the provider's, so it lives
 * in MechnariCopilot next to the labels it belongs with.
 */
export function CopilotProvider({ children }: { children: ReactNode }) {
  return (
    <CopilotKitProvider
      runtimeUrl="/api/copilotkit"
      // The inspector is a large debug panel that opens over the middle of
      // the page - directly on top of the intake form the copilot fills
      // in, which is the one thing a viewer needs to see. It is
      // development-only and can never render in production, so this
      // changes nothing about the deployed site; it is here so the local
      // run looks like the deployed one.
      //
      // `showDevConsole` is the wrong lever and v2 says so in its own
      // types: "This prop no longer controls the Inspector." It was set to
      // false here for a while and the panel still appeared.
      enableInspector={false}
    >
      {children}
    </CopilotKitProvider>
  );
}

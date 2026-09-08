"use client";

import { useEffect, useState } from "react";
import { CopilotPopup } from "@copilotkit/react-ui";
import { api } from "@/lib/api";

const READY_INITIAL =
  "Ask about a part, a failure mode, or why something scored the way it " +
  "did. Every number I quote comes from the deterministic engines - I " +
  "explain them, I don't compute them.";

/**
 * The CopilotKit popup, streaming from the ADK agent over AG-UI.
 *
 * Replaced a hand-rolled widget (CopilotChat.tsx, still in the repo,
 * unmounted) to get token-by-token streaming instead of one blocking
 * request.
 *
 * The health probe exists because of a real gap: when the agent fails,
 * AG-UI emits a RUN_ERROR, and CopilotKit's popup renders exactly nothing
 * for it - the chat just sits there. Asking the API up front whether the
 * key authenticates means the user is told why instead of watching a dead
 * box, which matters most in the exact situation where it's broken.
 *
 * The instructions below are framing only. They cannot loosen the real
 * constraint: the agent's tools are its only route to data, and none of
 * them can write a score. That is enforced in test_mechnari_tools.py.
 */
export function MechnariCopilot() {
  const [unavailable, setUnavailable] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .copilotHealth()
      .then((health) => {
        if (!cancelled && !health.api_key_works) {
          setUnavailable(health.reason || "The copilot is unavailable.");
        }
      })
      .catch(() => {
        if (!cancelled) setUnavailable("Can't reach the agent service.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <>
      <CopilotPopup
        instructions={
          "You are Mechnari's DFMEA copilot. Explain findings in plain " +
          "engineering English, and always cite the 8D or warranty record a " +
          "claim rests on. Never state a severity, occurrence, detection or " +
          "Action Priority that you did not read from a tool result - if you " +
          "do not have it, say so and name the tool that would have it."
        }
        labels={{
          title: "Ask Mechnari",
          initial: unavailable
            ? `⚠️ ${unavailable} The copilot can't answer until that's fixed - every score, gap and backtest figure in the app is unaffected, because none of them go through this key.`
            : READY_INITIAL,
          placeholder: unavailable ? "Copilot unavailable…" : "Ask a question…",
        }}
      />
    </>
  );
}

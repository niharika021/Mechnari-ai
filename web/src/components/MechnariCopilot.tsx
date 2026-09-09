"use client";

import { useEffect, useState } from "react";
import { CopilotSidebar } from "@copilotkit/react-core/v2";
import { api } from "@/lib/api";

const READY_INITIAL =
  "Ask about a part, a failure mode, or why something scored the way it " +
  "did — or just describe the part you're designing and I'll fill the form " +
  "in and run the analysis. Every number I quote comes from the " +
  "deterministic engines; I explain them, I don't compute them.";

/**
 * The copilot as a docked sidebar rather than a popup.
 *
 * A popup was the wrong shape for something that acts on the UI: it
 * covered the very form it was filling in, so the engineer could not see
 * the effect of what they had just asked for. Docked, the sheet and the
 * conversation are on screen together, which is the point - the agent's
 * actions are visible as they happen rather than described afterwards.
 *
 * v2 has no `instructions` prop, and the rules that used to live here have
 * moved to the ADK agent's own instruction in mechnari_agent/agent.py.
 * That is where they belonged: they were a second copy of rules the
 * backend agent already states, and two copies of a rule is one copy too
 * many for a rule about not fabricating numbers. Nothing was dropped -
 * `_UI_ACTIONS_RULE` and `_NUMBERS_RULE` carry it, and they now apply to
 * every caller of the agent rather than only to this sidebar.
 *
 * What is enforced rather than instructed: no tool exists for setting a
 * score or stamping a completion, on the frontend (CopilotActions.tsx) or
 * the backend (test_mechnari_tools.py). An agent cannot take an action it
 * has no tool for, whatever it is asked or told.
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
    <CopilotSidebar
      // Which agent to talk to is the chat's business in v2, not the
      // provider's. Must match the key in the runtime's `agents` map.
      agentId="mechnari"
      defaultOpen={false}
      labels={{
        modalHeaderTitle: "Ask Mechnari",
        welcomeMessageText: unavailable
          ? `${unavailable} I can't answer or act until that's fixed — every score, gap and backtest figure in the app is unaffected, because none of them go through this key.`
          : READY_INITIAL,
        chatInputPlaceholder: unavailable
          ? "Copilot unavailable…"
          : "Ask, or describe a part…",
      }}
    />
  );
}

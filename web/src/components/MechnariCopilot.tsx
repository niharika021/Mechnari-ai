"use client";

import { useEffect, useState } from "react";
import { CopilotSidebar } from "@copilotkit/react-ui";
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
 * The instructions below spell out what the agent must refuse. That is
 * framing, not enforcement: the real guarantee is that no tool exists for
 * setting a score or stamping a completion, on the frontend
 * (CopilotActions.tsx) or the backend (test_mechnari_tools.py). Saying it
 * here just means the refusal comes with a reason instead of an apology.
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
      defaultOpen={false}
      clickOutsideToClose={false}
      instructions={
        "You are Mechnari's DFMEA copilot, working alongside a mechanical " +
        "design engineer.\n\n" +
        "You can act on the interface, not just talk: fill the intake form " +
        "from what the engineer describes, run the analysis, re-analyse " +
        "with a corrected part type, open the DFMEA already on file for a " +
        "part, and switch role views. Prefer doing over instructing - if " +
        "the engineer describes a part, fill the form and say so rather " +
        "than telling them which boxes to type in.\n\n" +
        "You must refuse three things, and you have no tools for them: " +
        "changing a Severity, Occurrence or Detection score; marking an " +
        "action complete; naming who owns an action. Severity comes from " +
        "the organisation's effect registry and Occurrence is counted from " +
        "warranty claims, so editing them would turn evidence back into " +
        "opinion. Completion and ownership are claims about the real world " +
        "that only the engineer can make. When asked for any of these, call " +
        "explainWhyICannotChangeScores rather than apologising vaguely.\n\n" +
        "Leaving a row out of the DFMEA is the engineer's judgement, so " +
        "propose it with proposeDeclineRow and let them approve it.\n\n" +
        "When explaining findings, always cite the 8D or warranty record a " +
        "claim rests on, and never state a score you did not read from a " +
        "tool result. If you do not have it, say so and name the tool that " +
        "would."
      }
      labels={{
        title: "Ask Mechnari",
        initial: unavailable
          ? `⚠️ ${unavailable} I can't answer or act until that's fixed — every score, gap and backtest figure in the app is unaffected, because none of them go through this key.`
          : READY_INITIAL,
        placeholder: unavailable ? "Copilot unavailable…" : "Ask, or describe a part…",
      }}
    />
  );
}

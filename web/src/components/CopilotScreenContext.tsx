"use client";

import { useRef } from "react";
import { usePathname, useRouter } from "next/navigation";
import {
  type JsonSerializable,
  useAgentContext,
  useFrontendTool,
} from "@copilotkit/react-core/v2";
import { z } from "zod";

/**
 * What the agent knows regardless of which view is open.
 *
 * This is mounted in the root layout, and that placement is the whole
 * point. Everything else the copilot can do lives in CopilotActions,
 * which mounts inside PartIntake - so on /quality and /company the agent
 * previously had no tools and no context at all. It did not know which
 * screen the engineer was looking at, and could not move them off it:
 * "take me to the program view" from the review queue had nothing to
 * call and turned back into prose describing how to click.
 *
 * Two things are registered here:
 *
 * 1. Where the engineer is, and what that screen is for. Enough for the
 *    agent to interpret "this" and "here", and to notice when it is
 *    being asked for something the current screen cannot do.
 * 2. goToView, so navigation works from anywhere rather than only from
 *    the one page that happened to register it.
 *
 * Deliberately small. Context is stringified into every request, so it
 * costs tokens on every turn and pushes the actual question further from
 * the model's attention. Page-specific detail belongs in that page's own
 * CopilotFacts, where it appears only while that page is open.
 */

const VIEWS: Record<string, { name: string; purpose: string }> = {
  "/design": {
    name: "Design Engineer - Part Intake",
    purpose:
      "Drafting a DFMEA for a new part or package, or opening the one " +
      "already on file for an existing part. This is where findings are " +
      "reviewed and a report is generated.",
  },
  "/quality": {
    name: "Quality Engineer - Review Queue",
    purpose:
      "Auditing drafts submitted by design engineers against the " +
      "failure-effect registry and the warranty record, and closing out " +
      "actions. Reports are approved or returned here, not drafted.",
  },
  "/company": {
    name: "Company & Leadership - Risk Coverage",
    purpose:
      "A program-level rollup: coverage across parts, open safety gaps, " +
      "and the backtest evidence. No row-level editing happens here.",
  },
};

export function CopilotScreenContext() {
  const pathname = usePathname() || "";
  const router = useRouter();

  // Same stale-closure hazard as CopilotActions: goToView is registered
  // once and would otherwise keep comparing against whichever path was
  // current then, so "already on the quality view" could be said about a
  // view the engineer left several turns ago.
  const pathRef = useRef(pathname);
  pathRef.current = pathname;

  const key = Object.keys(VIEWS).find((k) => pathname.startsWith(k));
  const view = key ? VIEWS[key] : null;
  const onReportPage = /^\/design\/report\//.test(pathname);

  useAgentContext({
    description:
      "Which Mechnari screen the user is looking at right now, and what " +
      "that screen is for. Use it to interpret 'this' and 'here', and to " +
      "say plainly when something is done on a different view.",
    value: {
      path: pathname,
      view: onReportPage
        ? "Design Engineer - a generated DFMEA report"
        : view?.name ?? "unknown",
      purpose: onReportPage
        ? "Reading one generated report in full, where its actions can be " +
          "edited and marked done before it reaches Quality."
        : view?.purpose ?? "",
      available_views: ["design", "quality", "company"],
    },
  });

  useFrontendTool({
    name: "goToView",
    followUp: true,
    description:
      "Switch between the three role views: design (draft a DFMEA), " +
      "quality (review queue and part audits), company (program rollup). " +
      "Available from any screen.",
    parameters: z.object({
      view: z.string().describe("One of: design, quality, company."),
    }),
    handler: async ({ view: target }) => {
      const next = String(target).toLowerCase().trim();
      if (!["design", "quality", "company"].includes(next)) {
        return `"${target}" is not a view. The views are design, quality and company.`;
      }
      if (pathRef.current.startsWith(`/${next}`)) {
        // Saying so beats a silent no-op that reads as a broken tool.
        return `Already on the ${next} view.`;
      }
      router.push(`/${next}`);
      return `Opened the ${next} view.`;
    },
  });

  return null;
}

/**
 * Page-specific facts, registered only while that page is mounted.
 *
 * Split out so a page can hand the agent what is actually on screen
 * without every other page paying for it in tokens on every turn.
 */
export function CopilotFacts({
  description,
  value,
}: {
  description: string;
  value: { [key: string]: JsonSerializable };
}) {
  useAgentContext({ description, value });
  return null;
}

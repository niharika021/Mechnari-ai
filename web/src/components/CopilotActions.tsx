"use client";

import { useCopilotAction, useCopilotReadable } from "@copilotkit/react-core";
import { useRouter } from "next/navigation";

/**
 * What the copilot is allowed to do to the UI.
 *
 * The line drawn here is the same one the whole product rests on: the
 * agent may drive the tedium, and may not make the judgements. Data
 * entry, navigation, re-running an analysis with a corrected part type -
 * all fine, and all reversible by looking at the screen. What it must not
 * do is write a score, assert that work happened, or invent a commitment,
 * because those are the three things that would make the resulting DFMEA
 * a fabrication rather than a record.
 *
 * Two of those are enforced rather than merely discouraged: there is no
 * action here that sets Severity, Occurrence or Detection, and none that
 * stamps a completion date. An action the agent has no tool for is an
 * action it cannot take, whatever it is asked. test_mechnari_tools.py
 * makes the same guarantee on the backend tools; this is the frontend
 * half of it.
 *
 * Declining a row is the interesting middle case. It is a real
 * engineering judgement with audit consequences - Quality reads a
 * declined High row as "considered and rejected" - so the agent may
 * propose it and the engineer approves it inline. That is what
 * renderAndWaitForResponse is for.
 */

export type IntakeFields = {
  part_number?: string;
  description?: string;
  function?: string;
  material?: string;
  system_package?: string;
};

export type ActionHandlers = {
  fillIntake: (fields: IntakeFields) => void;
  build: () => void;
  reanalyseAs: (partTypeName: string) => boolean;
  openExisting: (partIdOrName: string) => boolean;
  declineRow: (modeId: string, reason: string) => boolean;
  /** Context the agent should know without being told - what is on screen. */
  context: Record<string, unknown>;
};

export function CopilotActions({ handlers }: { handlers: ActionHandlers }) {
  const router = useRouter();

  // Telling the agent what is currently on screen means it can answer
  // "why is this row High" about the row in front of the engineer rather
  // than asking which one.
  useCopilotReadable({
    description:
      "What the design engineer currently has on screen in Mechnari: the " +
      "intake fields, the stage of the workflow, and any rows under review.",
    value: handlers.context,
  });

  useCopilotAction({
    name: "fillPartIntake",
    description:
      "Fill in the new-part intake form. Use this when the engineer " +
      "describes a part in conversation instead of typing it into the " +
      "form. Only sets the descriptive fields - it cannot set any risk " +
      "score.",
    parameters: [
      { name: "part_number", type: "string", required: false,
        description: "The part number, if the engineer gave one." },
      { name: "description", type: "string", required: false,
        description: "Short part description, e.g. 'EPDM Fuel Return Line'." },
      { name: "function", type: "string", required: false,
        description: "The elementary function - what the part has to do." },
      { name: "material", type: "string", required: false,
        description: "Material or compound." },
    ],
    handler: async ({ part_number, description, function: fn, material }) => {
      handlers.fillIntake({
        part_number: part_number || undefined,
        description: description || undefined,
        function: fn || undefined,
        material: material || undefined,
      });
      return "Filled the intake form. The engineer can correct it before building.";
    },
  });

  useCopilotAction({
    name: "buildDfmea",
    description:
      "Run the analysis on whatever is currently in the intake form and " +
      "show the findings for review. Does not generate a report - the " +
      "engineer reviews the findings first.",
    parameters: [],
    handler: async () => {
      handlers.build();
      return "Running the analysis. The findings will appear for review.";
    },
  });

  useCopilotAction({
    name: "reanalyseAsPartType",
    description:
      "Re-run the analysis treating the part as a different part type, " +
      "when the engineer says the identified type is wrong. This changes " +
      "which failure modes are proposed, so it regenerates the findings.",
    parameters: [
      { name: "part_type_name", type: "string", required: true,
        description:
          "The part type to use, e.g. 'Structural Bracket / Mounting Plate'." },
    ],
    handler: async ({ part_type_name }) => {
      const ok = handlers.reanalyseAs(part_type_name);
      return ok
        ? `Re-analysing as ${part_type_name}. The proposed failure modes will change.`
        : `I could not match "${part_type_name}" to a known part type. Ask the engineer to pick it from the dropdown.`;
    },
  });

  useCopilotAction({
    name: "openExistingPartDfmea",
    description:
      "Open the DFMEA already on file for a part that exists in the BOM, " +
      "by part id (e.g. TR-FL-001) or by name. Shows what was filed, what " +
      "the warranty record says now, and which modes were never analysed.",
    parameters: [
      { name: "part", type: "string", required: true,
        description: "Part id such as TR-FL-001, or part name." },
    ],
    handler: async ({ part }) => {
      const ok = handlers.openExisting(part);
      return ok
        ? `Opened the DFMEA on file for ${part}.`
        : `I could not find a part matching "${part}" in the BOM.`;
    },
  });

  useCopilotAction({
    name: "goToView",
    description:
      "Switch between the three role views: design (draft a DFMEA), " +
      "quality (review queue and part audits), company (program rollup).",
    parameters: [
      { name: "view", type: "string", required: true,
        description: "One of: design, quality, company." },
    ],
    handler: async ({ view }) => {
      const target = String(view).toLowerCase().trim();
      if (!["design", "quality", "company"].includes(target)) {
        return `"${view}" is not a view. The views are design, quality and company.`;
      }
      router.push(`/${target}`);
      return `Opened the ${target} view.`;
    },
  });

  // Declining a row is a judgement, not a chore. The agent proposes; the
  // engineer decides, in the chat, before anything changes.
  useCopilotAction({
    name: "proposeDeclineRow",
    description:
      "Propose leaving a proposed failure mode out of the DFMEA. Use when " +
      "the engineer explains why a mode does not apply to this design. " +
      "This only proposes - the engineer must approve it, because Quality " +
      "reads a declined High row as a considered decision.",
    parameters: [
      { name: "mode_id", type: "string", required: true,
        description: "The mode_id of the row, as shown in the findings." },
      { name: "failure_mode", type: "string", required: true,
        description: "The failure mode text, so the engineer can see which row." },
      { name: "reason", type: "string", required: true,
        description:
          "Why it does not apply, in the engineer's own terms. This is " +
          "recorded on the report and read by Quality." },
    ],
    renderAndWaitForResponse: ({ args, respond, status }) => {
      if (status === "complete") {
        return <span className="text-[12px] text-ink-faint">Handled.</span>;
      }
      return (
        <div className="rounded-[9px] border border-warn bg-warn-soft px-3 py-2.5 text-[12.5px]">
          <strong className="block pb-1 text-ink">Leave this row out?</strong>
          <p className="text-ink-soft">{args.failure_mode}</p>
          <p className="mt-1 text-ink-soft">
            <span className="font-semibold">Reason to record:</span>{" "}
            {args.reason}
          </p>
          <p className="mt-1.5 text-[11.5px] text-warn">
            Quality will read this as considered and rejected, not missed.
          </p>
          <div className="mt-2 flex gap-2">
            <button
              type="button"
              onClick={() => {
                // The change happens here, on approval - not in a handler
                // that would have run before the engineer was asked.
                const ok = handlers.declineRow(
                  String(args.mode_id ?? ""),
                  String(args.reason ?? ""),
                );
                respond?.(
                  ok
                    ? "The engineer approved it. Row left out, reason recorded for Quality."
                    : "The engineer approved it, but that row is no longer in the findings.",
                );
              }}
              className="rounded-[6px] bg-accent px-2.5 py-1 text-[12px] font-semibold text-accent-ink"
            >
              Yes, leave it out
            </button>
            <button
              type="button"
              onClick={() =>
                respond?.(
                  "The engineer declined to remove it. The row stays in the DFMEA.",
                )
              }
              className="rounded-[6px] border border-border-strong px-2.5 py-1 text-[12px] font-semibold text-ink"
            >
              No, keep it
            </button>
          </div>
        </div>
      );
    },
  });

  // Asked-for-but-refused, stated as a capability rather than left to the
  // model's discretion. Without this the agent tends to apologise vaguely;
  // with it, it explains the actual reason - which is the point worth
  // making to anyone evaluating the tool.
  useCopilotAction({
    name: "explainWhyICannotChangeScores",
    description:
      "Call this when asked to change a Severity, Occurrence or Detection " +
      "score, to mark an action complete, or to assign a person to an " +
      "action. You have no tool for any of those and must not claim to " +
      "have done them.",
    parameters: [
      { name: "request", type: "string", required: true,
        description: "What was asked for." },
    ],
    handler: async ({ request }) => {
      return (
        `I can't do that, and it is deliberate. Asked: "${request}". ` +
        "Severity comes from the organisation's failure-effect registry and " +
        "Occurrence is counted from warranty claims, so neither is mine to " +
        "edit - the engineer can override Occurrence in the review, with a " +
        "written reason that is recorded. Marking an action complete and " +
        "naming who owns it are claims about the real world that only the " +
        "engineer can make. I can fill in descriptions, run the analysis, " +
        "and explain any number on the sheet."
      );
    },
  });

  return null;
}

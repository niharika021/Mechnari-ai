"use client";

import { useRef } from "react";
import {
  type JsonSerializable,
  useAgentContext,
  useFrontendTool,
  useHumanInTheLoop,
} from "@copilotkit/react-core/v2";
import { z } from "zod";

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
 * tool here that sets Severity, Occurrence or Detection, and none that
 * stamps a completion date. An action the agent has no tool for is an
 * action it cannot take, whatever it is asked. test_mechnari_tools.py
 * makes the same guarantee on the backend tools; this is the frontend
 * half of it.
 *
 * Declining a row is the interesting middle case. It is a real
 * engineering judgement with audit consequences - Quality reads a
 * declined High row as "considered and rejected" - so the agent may
 * propose it and the engineer approves it inline. That is what
 * useHumanInTheLoop is for.
 *
 * On the v2 API. Parameters are zod schemas rather than v1's
 * `parameters: [{ name, type, required }]` arrays, which is worth the
 * migration for exactly one reason: the handler's `args` are now typed
 * from the schema, so a field renamed here and not there is a compile
 * error instead of an undefined that quietly writes a blank into a form.
 *
 * --- Why every tool sets followUp ---
 * `followUp` defaults to FALSE in v2: "execute tool, add messages to
 * history, done". The tool runs and the agent never speaks again that
 * turn. Observed as the intake form filling in correctly while the chat
 * showed the engineer's own message and nothing after it - the run
 * ended at TOOL_CALL_END with no TEXT_MESSAGE at all.
 *
 * That is bad for the data-entry tools, which should confirm what they
 * changed, and much worse for explainWhyICannotChangeScores, whose
 * entire purpose is to say why a request was refused. Silently doing
 * nothing is the one response a refusal must never give.
 *
 * The v1 API re-ran the agent after a tool by default, so this
 * regressed on migration rather than never having worked. It was not
 * caught then because the tools were verified by watching the UI
 * change, which is exactly the half that still works.
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
  /**
   * Context the agent should know without being told - what is on screen.
   *
   * Typed as JsonSerializable rather than Record<string, unknown> because
   * CopilotKit stringifies it before sending: anything that is not JSON -
   * a Date, a function, a component - would silently reach the model as
   * null or vanish, and the agent would answer about a screen state that
   * is not the one in front of the engineer.
   */
  context: { [key: string]: JsonSerializable };
};

export function CopilotActions({ handlers }: { handlers: ActionHandlers }) {
  // Every tool below calls through this ref rather than closing over
  // `handlers` directly.
  //
  // The handlers close over React state - the intake rows, the review, the
  // part list - and a tool registered on one render keeps the closure it
  // was registered with. Asked to draft a DFMEA for a steel bracket, the
  // agent filled the form and then built on the next turn, and the analysis
  // came back for "EPDM Fuel Return Line, EXAMPLE-0001": the example row the
  // page starts with, because that was the state when buildDfmea was first
  // registered. The form on screen said Bracket. Nothing errored.
  //
  // It only became visible once a fill and a build could happen seconds
  // apart, which is the sequencing the parallel-call fix introduced.
  const handlersRef = useRef(handlers);
  handlersRef.current = handlers;


  // Telling the agent what is currently on screen means it can answer
  // "why is this row High" about the row in front of the engineer rather
  // than asking which one. (v1: useCopilotReadable.)
  useAgentContext({
    description:
      "What the design engineer currently has on screen in Mechnari: the " +
      "intake fields, the stage of the workflow, and any rows under review.",
    value: handlers.context,
  });

  useFrontendTool({
    name: "fillPartIntake",
    followUp: true,
    description:
      "Fill in the new-part intake form. Use this when the engineer " +
      "describes a part in conversation instead of typing it into the " +
      "form. Only sets the descriptive fields - it cannot set any risk " +
      "score.",
    parameters: z.object({
      part_number: z
        .string()
        .optional()
        .describe("The part number, if the engineer gave one."),
      description: z
        .string()
        .optional()
        .describe("Short part description, e.g. 'EPDM Fuel Return Line'."),
      function: z
        .string()
        .optional()
        .describe("The elementary function - what the part has to do."),
      material: z.string().optional().describe("Material or compound."),
    }),
    handler: async ({ part_number, description, function: fn, material }) => {
      handlersRef.current.fillIntake({
        part_number: part_number || undefined,
        description: description || undefined,
        function: fn || undefined,
        material: material || undefined,
      });
      return "Filled the intake form. The engineer can correct it before building.";
    },
  });

  useFrontendTool({
    name: "buildDfmea",
    followUp: true,
    description:
      "Run the analysis on whatever is currently in the intake form and " +
      "show the findings for review. Does not generate a report - the " +
      "engineer reviews the findings first.",
    parameters: z.object({}),
    handler: async () => {
      handlersRef.current.build();
      return "Running the analysis. The findings will appear for review.";
    },
  });

  useFrontendTool({
    name: "reanalyseAsPartType",
    followUp: true,
    description:
      "Re-run the analysis treating the part as a different part type, " +
      "when the engineer says the identified type is wrong. This changes " +
      "which failure modes are proposed, so it regenerates the findings.",
    parameters: z.object({
      part_type_name: z
        .string()
        .describe(
          "The part type to use, e.g. 'Structural Bracket / Mounting Plate'.",
        ),
    }),
    handler: async ({ part_type_name }) => {
      const ok = handlersRef.current.reanalyseAs(part_type_name);
      return ok
        ? `Re-analysing as ${part_type_name}. The proposed failure modes will change.`
        : `I could not match "${part_type_name}" to a known part type. Ask the engineer to pick it from the dropdown.`;
    },
  });

  useFrontendTool({
    name: "openExistingPartDfmea",
    followUp: true,
    description:
      "Open the DFMEA already on file for a part that exists in the BOM, " +
      "by part id (e.g. TR-FL-001) or by name. Shows what was filed, what " +
      "the warranty record says now, and which modes were never analysed.",
    parameters: z.object({
      part: z.string().describe("Part id such as TR-FL-001, or part name."),
    }),
    handler: async ({ part }) => {
      const ok = handlersRef.current.openExisting(part);
      return ok
        ? `Opened the DFMEA on file for ${part}.`
        : `I could not find a part matching "${part}" in the BOM.`;
    },
  });

  // goToView deliberately lives in CopilotScreenContext, not here.
  // Registered from this component it only existed on /design, so the
  // agent could not navigate away from the other two views - the one
  // place navigation is most useful. Registering it in both would mean
  // two tools with the same name whenever this component is mounted.

  // Declining a row is a judgement, not a chore. The agent proposes; the
  // engineer decides, in the chat, before anything changes.
  //
  // ReactHumanInTheLoop has no `handler` by construction - the type omits
  // it - which is a better shape than v1's, where `handler` and
  // `renderAndWaitForResponse` were both accepted but mutually exclusive
  // at runtime, and supplying both silently applied the change before the
  // engineer was asked.
  useHumanInTheLoop({
    name: "proposeDeclineRow",
    followUp: true,
    description:
      "Propose leaving a proposed failure mode out of the DFMEA. Use when " +
      "the engineer explains why a mode does not apply to this design. " +
      "This only proposes - the engineer must approve it, because Quality " +
      "reads a declined High row as a considered decision.",
    parameters: z.object({
      mode_id: z
        .string()
        .describe("The mode_id of the row, as shown in the findings."),
      failure_mode: z
        .string()
        .describe("The failure mode text, so the engineer can see which row."),
      reason: z
        .string()
        .describe(
          "Why it does not apply, in the engineer's own terms. This is " +
            "recorded on the report and read by Quality.",
        ),
    }),
    render: ({ args, respond, status }) => {
      if (status === "complete") {
        return <span className="text-label text-ink-faint">Handled.</span>;
      }
      return (
        <div className="rounded-md border border-warn bg-warn-soft px-3 py-2.5 text-label">
          <strong className="block pb-1 text-ink">Leave this row out?</strong>
          <p className="text-ink-soft">{args.failure_mode}</p>
          <p className="mt-1 text-ink-soft">
            <span className="font-semibold">Reason to record:</span>{" "}
            {args.reason}
          </p>
          <p className="mt-1.5 text-label text-warn">
            Quality will read this as considered and rejected, not missed.
          </p>
          <div className="mt-2 flex gap-2">
            <button
              type="button"
              disabled={!respond}
              onClick={() => {
                // The change happens here, on approval - not in a handler
                // that would have run before the engineer was asked.
                const ok = handlersRef.current.declineRow(
                  String(args.mode_id ?? ""),
                  String(args.reason ?? ""),
                );
                void respond?.(
                  ok
                    ? "The engineer approved it. Row left out, reason recorded for Quality."
                    : "The engineer approved it, but that row is no longer in the findings.",
                );
              }}
              className="rounded-[6px] bg-accent px-2.5 py-1 text-label font-semibold text-accent-ink disabled:opacity-50"
            >
              Yes, leave it out
            </button>
            <button
              type="button"
              disabled={!respond}
              onClick={() =>
                void respond?.(
                  "The engineer declined to remove it. The row stays in the DFMEA.",
                )
              }
              className="rounded-[6px] border border-border-strong px-2.5 py-1 text-label font-semibold text-ink disabled:opacity-50"
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
  useFrontendTool({
    name: "explainWhyICannotChangeScores",
    followUp: true,
    description:
      "Call this when asked to change a Severity, Occurrence or Detection " +
      "score, to mark an action complete, or to assign a person to an " +
      "action. You have no tool for any of those and must not claim to " +
      "have done them.",
    parameters: z.object({
      request: z.string().describe("What was asked for."),
    }),
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

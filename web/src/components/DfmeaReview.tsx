"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  api,
  type Neighbour,
  type PartType,
  type SheetResult,
  type SheetRow,
} from "@/lib/api";
import { AnalysisOverview } from "@/components/AnalysisOverview";
import { ApBadge, Button, Callout, Card, MetricTile } from "@/components/ui";

/**
 * The review stage: what Mechnari found, before it becomes a report.
 *
 * The engine proposes; the engineer decides. That was always the claim,
 * and this is where it is actually true - nothing reaches the final sheet
 * without passing through here.
 *
 * Which fields are editable is a deliberate line, not an oversight:
 *
 * - Detection, the design control, the test reference and the action are
 *   the engineer's. History supplies a starting point; the engineer knows
 *   the plan.
 * - Occurrence can be overridden but demands a written reason. It is
 *   measured from warranty claims, and free editing would quietly turn
 *   evidence back into opinion. A new design genuinely can remove a
 *   failure mechanism, so the override exists - it just has to be said
 *   out loud and it is recorded on the row.
 * - Severity is locked. It comes from the organisation's failure-effect
 *   registry, which is the only reason severity means the same thing on
 *   two engineers' sheets. One person lowering it locally would end that.
 *   Disagreement is raised as a flag against the registry instead.
 *
 * Action Priority is never recomputed here. Edited triples go back to
 * risk_engine via /api/rescore, so there is one AP table, in one place.
 */

export type Provenance = "proposed" | "edited" | "engineer_added";

export type ReviewRow = SheetRow & {
  include: boolean;
  provenance: Provenance;
  occurrence_evidence: number; // what the claims said, kept for the trail
  occurrence_override_reason: string;
  severity_disputed: boolean;
  severity_dispute_note: string;
  decline_reason: string;
  edited_fields: string[];
};

export type ReviewState = {
  partNumber: string;
  itemInterface: string;
  partTypeName: string;
  // The basis the rows were generated from. Kept because it is the thing
  // most worth checking first: the part type decides which failure modes
  // are even proposed, and it is often an inference rather than a fact.
  partTypeId: string;
  familyName: string;
  confidence: number;
  confirmed: boolean;
  typeReason: string;
  neighbours: Neighbour[];
  rows: ReviewRow[];
};

export function toReviewState(result: SheetResult): ReviewState[] {
  return result.items
    .filter((block) => block.status === "success")
    .map((block) => ({
      partNumber: block.part_number,
      itemInterface: block.item_interface ?? "",
      partTypeName: block.part_type_name ?? "",
      partTypeId: block.part_type_id ?? "",
      familyName: block.family_name ?? "",
      confidence: block.confidence ?? 0,
      confirmed: block.confirmed ?? false,
      typeReason: block.type_reason ?? "",
      neighbours: block.similar_parts ?? [],
      rows: block.rows.map((row) => ({
        ...row,
        include: true,
        provenance: "proposed" as Provenance,
        occurrence_evidence: row.occurrence,
        occurrence_override_reason: "",
        severity_disputed: false,
        severity_dispute_note: "",
        decline_reason: "",
        edited_fields: [],
      })),
    }));
}

let addedCounter = 0;

function blankEngineerRow(state: ReviewState): ReviewRow {
  addedCounter += 1;
  const base = state.rows[0];
  return {
    mode_id: `ENGINEER-${addedCounter}`,
    part_number: state.partNumber,
    item_interface: state.itemInterface,
    elementary_function: base?.elementary_function ?? "",
    material: base?.material ?? "",
    system_package: base?.system_package ?? "",
    failure_mode: "",
    potential_effect: "",
    system_level: "Component",
    severity: 5,
    potential_cause: "",
    drawing_spec: base?.drawing_spec ?? "",
    pes: base?.pes ?? "N",
    design_control_prevention: "",
    occurrence: 3,
    detection_control: "",
    test_reference: "",
    detection: 5,
    action_priority: "M",
    rpn_legacy: 75,
    recommended_action: "",
    responsibility: "",
    target_completion_date: "",
    action_taken: "",
    completed_date: "",
    // An engineer-added row has no warranty record behind it, and saying
    // so plainly is the honest thing - it is judgement, not evidence.
    evidence_ids: "",
    learned_from: "Engineer's own assessment (no warranty precedent)",
    field_reports: 0,
    field_claims: 0,
    claims_per_1000: null,
    scope_level: "ENGINEER",
    reassessed_severity: 5,
    reassessed_occurrence: 3,
    reassessed_detection: 5,
    reassessed_action_priority: "M",
    reassessed_rpn: 75,
    reassessment_basis: "",
    include: true,
    provenance: "engineer_added",
    occurrence_evidence: 3,
    occurrence_override_reason: "",
    severity_disputed: false,
    severity_dispute_note: "",
    decline_reason: "",
    edited_fields: [],
  };
}

export function DfmeaReview({
  initial,
  partTypes,
  apTableVerified,
  onGenerate,
  onBack,
  onReanalyse,
  reanalysing = false,
}: {
  initial: ReviewState[];
  partTypes: PartType[];
  apTableVerified: boolean;
  onGenerate: (states: ReviewState[]) => void;
  onBack: () => void;
  onReanalyse: (partNumber: string, partTypeId: string) => void;
  reanalysing?: boolean;
}) {
  const [states, setStates] = useState<ReviewState[]>(initial);

  // A re-analysis replaces the findings wholesale, so the review resets to
  // them rather than trying to merge edits onto rows that may no longer
  // exist. Losing edits is the correct behaviour here - they were made
  // against a basis the engineer has just rejected.
  const seeded = useRef(initial);
  useEffect(() => {
    if (initial !== seeded.current) {
      seeded.current = initial;
      setStates(initial);
    }
  }, [initial]);
  const [rescoring, setRescoring] = useState(false);
  const debounce = useRef<ReturnType<typeof setTimeout> | null>(null);

  const allRows = useMemo(() => states.flatMap((s) => s.rows), [states]);
  const included = allRows.filter((r) => r.include);
  const declinedHigh = allRows.filter((r) => !r.include && r.action_priority === "H");
  const missingReason = declinedHigh.filter((r) => !r.decline_reason.trim());
  const missingOverrideReason = included.filter(
    (r) => r.occurrence !== r.occurrence_evidence && !r.occurrence_override_reason.trim(),
  );
  const incompleteAdded = included.filter(
    (r) => r.provenance === "engineer_added" && !r.failure_mode.trim(),
  );

  const blockers: string[] = [];
  if (missingReason.length > 0)
    blockers.push(
      `${missingReason.length} declined High row(s) need a reason — Quality has to see why, not just that it is absent.`,
    );
  if (missingOverrideReason.length > 0)
    blockers.push(
      `${missingOverrideReason.length} row(s) override the warranty-measured Occurrence without a reason.`,
    );
  if (incompleteAdded.length > 0)
    blockers.push(`${incompleteAdded.length} added row(s) have no failure mode described.`);
  if (included.length === 0) blockers.push("No rows are included.");

  // Any S/O/D edit goes back to the engine for its Action Priority.
  function scheduleRescore(next: ReviewState[]) {
    if (debounce.current) clearTimeout(debounce.current);
    debounce.current = setTimeout(async () => {
      const flat = next.flatMap((s) => s.rows);
      if (flat.length === 0) return;
      setRescoring(true);
      try {
        const scored = await api.rescore(
          flat.map((r) => ({
            severity: r.severity,
            occurrence: r.occurrence,
            detection: r.detection,
          })),
        );
        let i = 0;
        setStates((prev) =>
          prev.map((s) => ({
            ...s,
            rows: s.rows.map((r) => {
              const s2 = scored[i++];
              return s2
                ? { ...r, action_priority: s2.action_priority, rpn_legacy: s2.rpn_legacy }
                : r;
            }),
          })),
        );
      } catch {
        // Leave the previous priority in place rather than showing a
        // number the engine did not produce.
      } finally {
        setRescoring(false);
      }
    }, 450);
  }

  useEffect(() => {
    return () => {
      if (debounce.current) clearTimeout(debounce.current);
    };
  }, []);

  function patchRow(si: number, modeId: string, patch: Partial<ReviewRow>, field?: string) {
    setStates((prev) => {
      const next = prev.map((s, i) =>
        i !== si
          ? s
          : {
              ...s,
              rows: s.rows.map((r) => {
                if (r.mode_id !== modeId) return r;
                const edited =
                  field && !r.edited_fields.includes(field)
                    ? [...r.edited_fields, field]
                    : r.edited_fields;
                const provenance: Provenance =
                  r.provenance === "engineer_added"
                    ? "engineer_added"
                    : edited.length > 0
                      ? "edited"
                      : "proposed";
                const updated: ReviewRow = {
                  ...r,
                  ...patch,
                  edited_fields: edited,
                  provenance,
                };
                return updated;
              }),
            },
      );
      if (patch.detection !== undefined || patch.occurrence !== undefined || patch.severity !== undefined) {
        scheduleRescore(next);
      }
      return next;
    });
  }

  return (
    <div className="flex flex-col gap-5">
      <Card className="px-5 py-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h3 className="font-display text-[15px] font-semibold text-ink">
              Review before the report — {allRows.length} rows found
            </h3>
            <p className="mt-1 max-w-[82ch] text-xs leading-relaxed text-ink-faint">
              These are findings, not a report. Nothing here reaches the DFMEA
              until you say so. Drop what does not apply, correct what you know
              better, add what history could not know — then generate.
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            {rescoring ? (
              <span className="font-mono text-[10.5px] text-ink-faint">rescoring…</span>
            ) : null}
            <Button onClick={onBack}>← Change the inputs</Button>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-px overflow-hidden rounded-[10px] border border-border bg-border sm:grid-cols-4">
          <div className="bg-bg">
            <MetricTile label="Included" value={`${included.length}/${allRows.length}`} />
          </div>
          <div className="bg-bg">
            <MetricTile
              label="You edited"
              value={allRows.filter((r) => r.provenance === "edited").length}
            />
          </div>
          <div className="bg-bg">
            <MetricTile
              label="You added"
              value={allRows.filter((r) => r.provenance === "engineer_added").length}
              tone="accent"
            />
          </div>
          <div className="bg-bg">
            <MetricTile
              label="High declined"
              value={declinedHigh.length}
              tone={declinedHigh.length > 0 ? "crit" : "default"}
            />
          </div>
        </div>
      </Card>

      {states.map((state, si) => (
        <Card key={`${state.partNumber}-${si}`} className="px-5 py-4">
          <div className="flex flex-wrap items-baseline gap-x-3">
            <span className="font-mono text-sm font-semibold text-accent">
              {state.partNumber || "(no part number)"}
            </span>
            <h4 className="font-display text-[14px] font-semibold text-ink">
              {state.itemInterface}
            </h4>
            <span className="text-xs text-ink-faint">{state.partTypeName}</span>
          </div>

          <div className="mt-3">
            <AnalysisOverview
              state={state}
              partTypes={partTypes}
              apTableVerified={apTableVerified}
              reanalysing={reanalysing}
              onReanalyse={(partTypeId) =>
                onReanalyse(state.partNumber, partTypeId)
              }
            />
          </div>

          <div className="mt-3 flex flex-col gap-2.5">
            {state.rows.map((row) => (
              <ReviewRowCard
                key={row.mode_id}
                row={row}
                onPatch={(patch, field) => patchRow(si, row.mode_id, patch, field)}
              />
            ))}
          </div>

          <div className="mt-3">
            <Button
              onClick={() =>
                setStates((prev) =>
                  prev.map((s, i) =>
                    i === si ? { ...s, rows: [...s.rows, blankEngineerRow(s)] } : s,
                  ),
                )
              }
            >
              + Add a failure mode from your own experience
            </Button>
          </div>
        </Card>
      ))}

      <Card className="px-5 py-4">
        {blockers.length > 0 ? (
          <div className="mb-3">
            <Callout tone="warn">
              <strong className="block pb-1">Before generating:</strong>
              <ul className="flex flex-col gap-0.5">
                {blockers.map((b) => (
                  <li key={b}>{b}</li>
                ))}
              </ul>
            </Callout>
          </div>
        ) : null}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="max-w-[70ch] text-[13px] text-ink-soft">
            {included.length} row{included.length === 1 ? "" : "s"} will go into the
            report, each recording whether it came from the evidence, from your
            edit, or from your own assessment. You are not signing it off here -
            next you work the actions, and Quality does the approving.
          </p>
          <Button
            variant="primary"
            disabled={blockers.length > 0}
            onClick={() => onGenerate(states)}
          >
            Generate the DFMEA report
          </Button>
        </div>
      </Card>
    </div>
  );
}

function ReviewRowCard({
  row,
  onPatch,
}: {
  row: ReviewRow;
  onPatch: (patch: Partial<ReviewRow>, field?: string) => void;
}) {
  const [open, setOpen] = useState(
    row.provenance === "engineer_added" || row.action_priority === "H",
  );
  const overridden = row.occurrence !== row.occurrence_evidence;

  return (
    <div
      className={`rounded-[9px] border bg-surface ${
        row.include ? "border-border" : "border-border-strong opacity-60"
      }`}
    >
      <div className="flex items-center gap-3 px-3.5 py-2.5">
        <input
          type="checkbox"
          checked={row.include}
          onChange={(e) => onPatch({ include: e.target.checked })}
          aria-label="Include this row"
          className="h-4 w-4 accent-accent"
        />
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="flex flex-1 items-center gap-2 text-left"
        >
          <span className="w-3 text-ink-faint">{open ? "▾" : "▸"}</span>
          <span className="flex-1 text-[13px] font-semibold text-ink">
            {row.failure_mode || (
              <span className="text-warn">Describe this failure mode…</span>
            )}
          </span>
          {row.provenance !== "proposed" ? (
            <span
              className={`rounded-full px-2 py-0.5 font-mono text-[9.5px] uppercase tracking-wide ${
                row.provenance === "engineer_added"
                  ? "bg-accent-soft text-accent-strong"
                  : "bg-warn-soft text-warn"
              }`}
            >
              {row.provenance === "engineer_added" ? "yours" : "edited"}
            </span>
          ) : null}
          <span className="font-mono text-[11px] text-ink-soft">
            S{row.severity} O{row.occurrence} D{row.detection}
          </span>
          <ApBadge ap={row.action_priority} />
        </button>
      </div>

      {open ? (
        <div className="border-t border-border px-3.5 py-3">
          {row.provenance === "engineer_added" ? (
            <div className="mb-3">
              <Callout tone="accent">
                Your own row. It carries no warranty record, and the report will
                say so — that is honest, not a weakness.
              </Callout>
            </div>
          ) : (
            <p className="mb-3 text-xs text-ink-faint">
              Learned from {row.learned_from}
              {row.evidence_ids ? (
                <>
                  {" · "}
                  <span className="font-mono text-[10.5px]">{row.evidence_ids}</span>
                </>
              ) : null}
            </p>
          )}

          <div className="grid gap-3 md:grid-cols-2">
            <EditField
              label="Potential failure mode"
              value={row.failure_mode}
              onChange={(v) => onPatch({ failure_mode: v }, "failure_mode")}
            />
            <EditField
              label="Potential effect"
              value={row.potential_effect}
              onChange={(v) => onPatch({ potential_effect: v }, "potential_effect")}
            />
            <EditField
              label="Potential cause"
              value={row.potential_cause}
              onChange={(v) => onPatch({ potential_cause: v }, "potential_cause")}
            />
            <EditField
              label="Current design control (prevention)"
              value={row.design_control_prevention}
              onChange={(v) =>
                onPatch({ design_control_prevention: v }, "design_control_prevention")
              }
            />
            <EditField
              label="Detection control"
              value={row.detection_control}
              onChange={(v) => onPatch({ detection_control: v }, "detection_control")}
            />
            <EditField
              label="Test reference number"
              value={row.test_reference}
              onChange={(v) => onPatch({ test_reference: v }, "test_reference")}
            />
            <div className="md:col-span-2">
              <EditField
                label="Recommended action"
                value={row.recommended_action}
                onChange={(v) => onPatch({ recommended_action: v }, "recommended_action")}
              />
            </div>
            <EditField
              label="Responsibility"
              value={row.responsibility}
              onChange={(v) => onPatch({ responsibility: v }, "responsibility")}
            />
            <EditField
              label="Target completion date"
              value={row.target_completion_date}
              onChange={(v) =>
                onPatch({ target_completion_date: v }, "target_completion_date")
              }
              placeholder="YYYY-MM-DD"
            />
          </div>

          <div className="mt-3.5 grid gap-3 sm:grid-cols-3">
            {/* Severity is registry-owned. Locked on purpose. */}
            <div>
              <LabelRow label="Severity" note="from the effect registry" />
              <div className="flex items-center gap-2">
                <span className="rounded-[7px] border border-border bg-bg-elevated px-3 py-2 font-mono text-sm text-ink">
                  {row.severity}
                </span>
                <button
                  type="button"
                  onClick={() => onPatch({ severity_disputed: !row.severity_disputed })}
                  className={`text-[11px] font-semibold ${
                    row.severity_disputed ? "text-warn" : "text-ink-faint hover:text-ink"
                  }`}
                >
                  {row.severity_disputed ? "disputing" : "dispute this"}
                </button>
              </div>
              {row.severity_disputed ? (
                <input
                  value={row.severity_dispute_note}
                  onChange={(e) => onPatch({ severity_dispute_note: e.target.value })}
                  placeholder="Why the registry severity looks wrong for this effect"
                  className="mt-1.5 w-full rounded-[7px] border border-warn bg-warn-soft px-2.5 py-1.5 text-[12px] text-ink placeholder:text-ink-faint focus:outline-none"
                />
              ) : null}
            </div>

            {/* Occurrence: overridable, but the reason is not optional. */}
            <div>
              <LabelRow
                label="Occurrence"
                note={`warranty measured ${row.occurrence_evidence}`}
              />
              <input
                type="number"
                min={1}
                max={10}
                value={row.occurrence}
                onChange={(e) =>
                  onPatch({ occurrence: clamp(e.target.value, row.occurrence) }, "occurrence")
                }
                className={`w-full rounded-[7px] border bg-bg-elevated px-3 py-2 font-mono text-sm text-ink focus:outline-none ${
                  overridden ? "border-warn" : "border-border-strong focus:border-accent"
                }`}
              />
              {overridden ? (
                <input
                  value={row.occurrence_override_reason}
                  onChange={(e) => onPatch({ occurrence_override_reason: e.target.value })}
                  placeholder="Required: why the claims rate does not apply"
                  className="mt-1.5 w-full rounded-[7px] border border-warn bg-warn-soft px-2.5 py-1.5 text-[12px] text-ink placeholder:text-ink-faint focus:outline-none"
                />
              ) : null}
            </div>

            <div>
              <LabelRow label="Detection" note="yours to set" />
              <input
                type="number"
                min={1}
                max={10}
                value={row.detection}
                onChange={(e) =>
                  onPatch({ detection: clamp(e.target.value, row.detection) }, "detection")
                }
                className="w-full rounded-[7px] border border-border-strong bg-bg-elevated px-3 py-2 font-mono text-sm text-ink focus:border-accent focus:outline-none"
              />
            </div>
          </div>

          {!row.include ? (
            <div className="mt-3">
              <LabelRow
                label="Reason for leaving this out"
                note={row.action_priority === "H" ? "required for a High row" : "optional"}
              />
              <input
                value={row.decline_reason}
                onChange={(e) => onPatch({ decline_reason: e.target.value })}
                placeholder="e.g. this interface does not exist on the new design"
                className={`w-full rounded-[7px] border bg-bg-elevated px-3 py-2 text-[12.5px] text-ink placeholder:text-ink-faint focus:outline-none ${
                  row.action_priority === "H" && !row.decline_reason.trim()
                    ? "border-warn"
                    : "border-border-strong focus:border-accent"
                }`}
              />
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function clamp(raw: string, fallback: number): number {
  const n = Number.parseInt(raw, 10);
  if (Number.isNaN(n)) return fallback;
  return Math.min(10, Math.max(1, n));
}

function LabelRow({ label, note }: { label: string; note?: string }) {
  return (
    <div className="mb-1 flex items-baseline gap-1.5">
      <span className="font-mono text-[10px] uppercase tracking-wider text-ink-faint">
        {label}
      </span>
      {note ? <span className="text-[10px] text-ink-faint">({note})</span> : null}
    </div>
  );
}

function EditField({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <div>
      <LabelRow label={label} />
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        rows={2}
        className="w-full resize-y rounded-[7px] border border-border-strong bg-bg-elevated px-2.5 py-1.5 text-[12.5px] leading-relaxed text-ink placeholder:text-ink-faint focus:border-accent focus:outline-none"
      />
    </div>
  );
}

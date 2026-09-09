"use client";

import { useState } from "react";
import type { PartType } from "@/lib/api";
import type { ReviewState } from "@/components/DfmeaReview";
import { Button, Callout, Card, Select } from "@/components/ui";

/**
 * What the analysis actually rests on, shown before the rows are argued
 * about.
 *
 * The part type is the reason this screen exists. It decides which
 * failure modes are proposed at all, and it is usually an inference from
 * a handful of neighbours rather than a fact - 44% of a neighbour vote is
 * a guess worth checking. Reviewing 22 rows generated from a wrong type
 * is wasted work, so the type is correctable here and correcting it
 * regenerates the rows rather than merely annotating them.
 *
 * The standards panel is not decoration either. An engineer signing this
 * needs to know Severity came from the organisation's registry rather
 * than a workshop opinion, Occurrence from counted claims, and that the
 * AP table is still provisional. Those are the claims the document rests
 * on, so they are stated where they can be checked.
 */
export function AnalysisOverview({
  state,
  partTypes,
  apTableVerified,
  onReanalyse,
  reanalysing,
}: {
  state: ReviewState;
  partTypes: PartType[];
  apTableVerified: boolean;
  onReanalyse: (partTypeId: string) => void;
  reanalysing: boolean;
}) {
  const [chosenType, setChosenType] = useState(state.partTypeId);

  const rows = state.rows;
  // Distinct 8D records across the rows - the same report often backs
  // several modes, so a naive sum would overstate the evidence base.
  const records = new Set<string>();
  for (const row of rows) {
    for (const id of (row.evidence_ids ?? "").split(",")) {
      const trimmed = id.trim();
      if (trimmed) records.add(trimmed);
    }
  }
  const claims = rows.reduce((sum, r) => sum + (r.field_claims ?? 0), 0);
  const highRows = rows.filter((r) => r.action_priority === "H").length;
  const safetyRows = rows.filter((r) => r.severity >= 9).length;
  const typeLevel = rows.filter((r) => r.scope_level === "TYPE").length;
  const familyLevel = rows.filter((r) => r.scope_level === "FAMILY").length;

  const typeChanged = chosenType !== state.partTypeId;

  return (
    <Card className="px-5 py-4">
      <h4 className="font-display text-[14px] font-semibold text-ink">
        What this analysis is based on
      </h4>
      <p className="mt-1 max-w-[82ch] text-xs leading-relaxed text-ink-faint">
        Check the basis before the rows. If the part type below is wrong, the
        failure modes proposed from it are wrong too — correcting it here
        regenerates them.
      </p>

      {/* ---- 1. What kind of part, and how sure ---- */}
      <div className="mt-4 rounded-[9px] border border-border bg-bg-elevated px-4 py-3.5">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div className="min-w-[260px] flex-1">
            <div className="mb-1 font-mono text-[10px] uppercase tracking-wider text-ink-faint">
              Identified as
            </div>
            <Select value={chosenType} onChange={(e) => setChosenType(e.target.value)}>
              {[...partTypes]
                .sort((a, b) => a.part_type_name.localeCompare(b.part_type_name))
                .map((pt) => (
                  <option key={pt.part_type_id} value={pt.part_type_id}>
                    {pt.part_type_name}
                  </option>
                ))}
            </Select>
          </div>
          <div className="text-right">
            <div className="mb-1 font-mono text-[10px] uppercase tracking-wider text-ink-faint">
              Confidence
            </div>
            <span
              className={`font-mono text-lg font-bold ${
                state.confirmed
                  ? "text-ok"
                  : state.confidence >= 0.6
                    ? "text-ink"
                    : "text-warn"
              }`}
            >
              {state.confirmed ? "confirmed" : `${Math.round(state.confidence * 100)}%`}
            </span>
          </div>
          {typeChanged ? (
            <Button
              variant="primary"
              onClick={() => onReanalyse(chosenType)}
              disabled={reanalysing}
            >
              {reanalysing ? "Re-analysing…" : "↻ Re-analyse with this type"}
            </Button>
          ) : null}
        </div>

        <p className="mt-2 text-xs text-ink-soft">
          Family: {state.familyName}
        </p>

        {!state.confirmed && state.confidence < 0.6 ? (
          <div className="mt-2.5">
            <Callout tone="warn">
              {state.typeReason || "The neighbours disagree on what kind of part this is."}
            </Callout>
          </div>
        ) : null}
      </div>

      {/* ---- 2. Where the history came from ---- */}
      <div className="mt-3 grid gap-3 lg:grid-cols-2">
        <div className="rounded-[9px] border border-border bg-bg-elevated px-4 py-3.5">
          <div className="mb-2 font-mono text-[10px] uppercase tracking-wider text-ink-faint">
            Similar parts found in the warranty record
          </div>
          {state.neighbours.length === 0 ? (
            <p className="text-xs text-ink-faint">
              No close historical part — this analysis is running cold, from the
              description alone.
            </p>
          ) : (
            <ul className="flex flex-col gap-1.5">
              {state.neighbours.map((n) => (
                <li key={n.part_id} className="flex items-baseline gap-2 text-[12.5px]">
                  <span className="w-11 shrink-0 font-mono text-accent">
                    {n.similarity.toFixed(3)}
                  </span>
                  <span className="flex-1 text-ink">{n.item_reference}</span>
                  <span className="font-mono text-[10px] text-ink-faint">
                    {n.part_id}
                  </span>
                </li>
              ))}
            </ul>
          )}
          <p className="mt-2 text-[11px] leading-snug text-ink-faint">
            Similarity is cosine distance on the part description, function and
            material. It ranks candidates; it does not decide anything on its own.
          </p>
        </div>

        <div className="rounded-[9px] border border-border bg-bg-elevated px-4 py-3.5">
          <div className="mb-2 font-mono text-[10px] uppercase tracking-wider text-ink-faint">
            Evidence behind the proposal
          </div>
          <dl className="flex flex-col gap-1.5 text-[12.5px]">
            <Stat label="Failure modes proposed" value={rows.length} />
            <Stat label="Distinct 8D / warranty records" value={records.size} />
            <Stat label="Field claims behind them" value={claims.toLocaleString()} />
            <Stat
              label="Learned at part-type level"
              value={`${typeLevel} row${typeLevel === 1 ? "" : "s"}`}
            />
            <Stat
              label="Learned at family level"
              value={`${familyLevel} row${familyLevel === 1 ? "" : "s"}`}
            />
            <Stat label="High priority" value={highRows} tone={highRows > 0 ? "crit" : undefined} />
            <Stat
              label="Severity 9+"
              value={safetyRows}
              tone={safetyRows > 0 ? "crit" : undefined}
            />
          </dl>
        </div>
      </div>

      {/* ---- 3. The standards this rests on ---- */}
      <div className="mt-3 rounded-[9px] border border-border bg-bg-elevated px-4 py-3.5">
        <div className="mb-2 font-mono text-[10px] uppercase tracking-wider text-ink-faint">
          Standards and rules applied
        </div>
        <ul className="flex flex-col gap-1.5 text-[12.5px] leading-relaxed text-ink-soft">
          <li>
            <strong className="text-ink">Ranking: AIAG-VDA Action Priority</strong> (2019),
            read severity-first — not RPN. Multiplication misranks risk, so RPN is
            carried only as a legacy column.
            {!apTableVerified ? (
              <span className="text-warn">
                {" "}
                The DFMEA AP table is still provisional pending a check against the
                published handbook.
              </span>
            ) : null}
          </li>
          <li>
            <strong className="text-ink">Severity: the organisation&apos;s
            failure-effect registry.</strong> One severity per effect, company-wide —
            which is the only reason it means the same thing on two engineers&apos;
            sheets. Not editable per row.
          </li>
          <li>
            <strong className="text-ink">Occurrence: counted from warranty
            claims</strong> (claims per 1,000 units in service), not estimated in a
            workshop. Overridable, but only with a written reason.
          </li>
          <li>
            <strong className="text-ink">Detection: floored by where the mode has
            actually escaped to.</strong> If a failure reached dealer service, the
            detection score cannot claim it is caught on the line.
          </li>
          <li>
            <strong className="text-ink">Every number comes from a deterministic
            engine.</strong> The language model explains findings; it is given no tool
            that can write a score.
          </li>
        </ul>
      </div>
    </Card>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: string | number;
  tone?: "crit";
}) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="text-ink-soft">{label}</dt>
      <dd
        className={`font-mono font-semibold ${
          tone === "crit" ? "text-crit" : "text-ink"
        }`}
      >
        {value}
      </dd>
    </div>
  );
}

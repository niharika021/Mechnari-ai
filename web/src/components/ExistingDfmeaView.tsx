"use client";

import type { ExistingDfmea, FiledRow } from "@/lib/api";
import { ApBadge, Callout, Card, MetricTile } from "@/components/ui";

/**
 * The DFMEA already on file for an existing part.
 *
 * The filed numbers are shown next to what the warranty record says now,
 * rather than being replaced by it. The filed value is what somebody
 * signed; the evidence value is what the claims show. Keeping the pair
 * visible is the finding - and it is what an auditor asks to see.
 */
export function ExistingDfmeaView({ data }: { data: ExistingDfmea }) {
  return (
    <div className="flex flex-col gap-5">
      <Card className="px-5 py-4">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <span className="font-mono text-sm font-semibold text-accent">
            {data.part_id}
          </span>
          <h3 className="font-display text-[15px] font-semibold text-ink">
            {data.item_reference}
          </h3>
          <span className="text-xs text-ink-faint">{data.part_type_name}</span>
        </div>
        <p className="mt-1.5 max-w-[85ch] text-[13px] text-ink-soft">
          {data.elementary_function}
        </p>
        <p className="mt-1 text-xs text-ink-faint">
          {data.material} · {data.system_package}
          {data.drawing_spec ? ` · ${data.drawing_spec}` : ""}
        </p>
        {data.analyzed_by ? (
          <p className="mt-2 font-mono text-[11px] text-ink-faint">
            On file: analysed by {data.analyzed_by} on {data.analysis_date} ({data.revision})
          </p>
        ) : null}

        <div className="mt-4 grid grid-cols-2 gap-px overflow-hidden rounded-[10px] border border-border bg-border sm:grid-cols-4">
          <div className="bg-bg">
            <MetricTile
              label="Rows on file"
              value={`${data.rows_analysed}/${data.rows_applicable}`}
              hint="analysed / applicable"
            />
          </div>
          <div className="bg-bg">
            <MetricTile
              label="Coverage"
              value={`${data.coverage_pct}%`}
              tone={data.coverage_pct < 70 ? "crit" : "default"}
            />
          </div>
          <div className="bg-bg">
            <MetricTile
              label="Rows evidence disputes"
              value={data.rows_disagreeing}
              tone={data.rows_disagreeing > 0 ? "crit" : "default"}
            />
          </div>
          <div className="bg-bg">
            <MetricTile
              label="Warranty issues on record"
              value={data.own_history.length}
            />
          </div>
        </div>
      </Card>

      {data.filed_rows.length === 0 ? (
        <Callout tone="crit">
          There is no DFMEA on file for this part at all, yet{" "}
          {data.missing_rows.length} failure mode(s) are applicable to this kind
          of part.
        </Callout>
      ) : (
        <Card className="px-5 py-4">
          <h4 className="font-display text-[14px] font-semibold text-ink">
            DFMEA on file — {data.filed_rows.length} row
            {data.filed_rows.length === 1 ? "" : "s"}
          </h4>
          <p className="mt-1 max-w-[80ch] text-xs leading-relaxed text-ink-faint">
            Filed scores shown as signed, next to what the warranty record puts
            them at now. Where the two differ the row is flagged — the filed
            document is not edited, the disagreement is.
          </p>
          <div className="mt-3 overflow-x-auto rounded-[8px] border border-border">
            <table className="min-w-[1500px] border-collapse text-left text-[12px]">
              <thead>
                <tr className="border-b border-border bg-bg-elevated font-mono text-[9.5px] uppercase tracking-wide text-ink-faint">
                  <th className="border-r border-border px-2 py-2">Failure mode</th>
                  <th className="border-r border-border px-2 py-2">Effect</th>
                  <th className="border-r border-border px-2 py-2">Cause</th>
                  <th className="border-r border-border px-2 py-2">Design control on file</th>
                  <th className="border-r border-border px-2 py-2 text-center" colSpan={4}>
                    As filed
                  </th>
                  <th className="border-r border-border px-2 py-2 text-center" colSpan={4}>
                    Evidence says
                  </th>
                  <th className="px-2 py-2">8D records</th>
                </tr>
                <tr className="border-b border-border bg-bg-elevated font-mono text-[9.5px] uppercase tracking-wide text-ink-faint">
                  <th className="border-r border-border px-2 py-1"></th>
                  <th className="border-r border-border px-2 py-1"></th>
                  <th className="border-r border-border px-2 py-1"></th>
                  <th className="border-r border-border px-2 py-1"></th>
                  <th className="border-r border-border px-2 py-1 text-center">S</th>
                  <th className="border-r border-border px-2 py-1 text-center">O</th>
                  <th className="border-r border-border px-2 py-1 text-center">D</th>
                  <th className="border-r border-border px-2 py-1 text-center">AP</th>
                  <th className="border-r border-border px-2 py-1 text-center">S</th>
                  <th className="border-r border-border px-2 py-1 text-center">O</th>
                  <th className="border-r border-border px-2 py-1 text-center">D</th>
                  <th className="border-r border-border px-2 py-1 text-center">AP</th>
                  <th className="px-2 py-1"></th>
                </tr>
              </thead>
              <tbody>
                {data.filed_rows.map((row) => (
                  <FiledTableRow key={row.mode_id} row={row} />
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {data.missing_rows.length > 0 ? (
        <Card className="px-5 py-4">
          <h4 className="font-display text-[14px] font-semibold text-ink">
            Applicable but never analysed — {data.missing_rows.length} row
            {data.missing_rows.length === 1 ? "" : "s"}
          </h4>
          <p className="mt-1 max-w-[80ch] text-xs leading-relaxed text-ink-faint">
            Proven on this kind of part elsewhere in the company, and absent
            from this part&apos;s DFMEA. Each carries the warranty record it
            came from.
          </p>
          <div className="mt-3 flex flex-col gap-2">
            {data.missing_rows.map((gap) => (
              <div
                key={gap.failure_mode}
                className="rounded-[8px] border border-border bg-surface px-3 py-2.5"
              >
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                  <span className="text-[13px] font-semibold text-ink">
                    {gap.failure_mode}
                  </span>
                  <span
                    className={`font-mono text-xs ${
                      gap.standard_severity >= 9 ? "font-semibold text-crit" : "text-ink-soft"
                    }`}
                  >
                    S{gap.standard_severity}
                  </span>
                  <span className="ml-auto font-mono text-[10px] text-ink-faint">
                    {gap.evidence_ids}
                  </span>
                </div>
                <p className="mt-1 text-xs text-ink-soft">
                  Learned from {gap.learned_from}
                </p>
              </div>
            ))}
          </div>
        </Card>
      ) : (
        <Callout tone="ok">
          Every failure mode applicable to this kind of part is covered by the
          DFMEA on file.
        </Callout>
      )}
    </div>
  );
}

function FiledTableRow({ row }: { row: FiledRow }) {
  return (
    <>
      <tr className="border-b border-border align-top hover:bg-surface-hover">
        <td className="border-r border-border px-2 py-2 font-semibold text-ink">
          {row.failure_mode}
        </td>
        <td className="border-r border-border px-2 py-2 text-ink-soft">
          {row.potential_effect}
        </td>
        <td className="border-r border-border px-2 py-2 text-ink-soft">
          {row.potential_cause}
        </td>
        <td className="border-r border-border px-2 py-2 text-ink-soft">
          {row.design_control_prevention}
        </td>

        <Num value={row.severity} />
        <Num value={row.occurrence} />
        <Num value={row.detection} />
        <td className="border-r border-border px-2 py-2 text-center">
          <ApBadge ap={row.action_priority} />
        </td>

        <Num value={row.evidence_severity} changed={row.evidence_severity !== row.severity} />
        <Num value={row.evidence_occurrence} changed={row.evidence_occurrence !== row.occurrence} />
        <Num value={row.evidence_detection} changed={row.evidence_detection !== row.detection} />
        <td className="border-r border-border px-2 py-2 text-center">
          <ApBadge ap={row.evidence_action_priority} />
        </td>

        <td className="px-2 py-2 font-mono text-[10px] text-ink-soft">
          {row.evidence_ids}
          {row.evidence_scope ? (
            <span className="mt-0.5 block text-ink-faint">{row.evidence_scope}</span>
          ) : null}
        </td>
      </tr>
      {row.disagrees ? (
        <tr className="border-b border-border bg-warn-soft">
          <td colSpan={13} className="px-2 py-1.5 text-[11.5px] leading-relaxed text-warn">
            ⚠ {row.disagreement_notes}
          </td>
        </tr>
      ) : null}
    </>
  );
}

function Num({ value, changed = false }: { value: number; changed?: boolean }) {
  return (
    <td
      className={`border-r border-border px-2 py-2 text-center font-mono ${
        changed ? "font-semibold text-warn" : "text-ink-soft"
      }`}
    >
      {value}
    </td>
  );
}

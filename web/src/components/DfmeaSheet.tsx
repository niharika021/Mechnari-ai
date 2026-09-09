"use client";

import { useState } from "react";
import { api, ApiError, type SheetItemBlock, type SheetResult, type SheetRow } from "@/lib/api";
import { ApBadge, Button, Callout, Card } from "@/components/ui";

/**
 * The DFMEA rendered in the AIAG-VDA form sheet layout - the same column
 * groups engineers already fill in on paper, so the output needs no
 * translating before it goes into a review.
 *
 * Two columns are deliberately empty: RESPONSIBILITY and TARGET
 * COMPLETION DATE. Those are commitments, and inventing an owner or a
 * date would be inventing a commitment nobody made.
 *
 * The Reassessment of Risk block is filled in, and that is the part a
 * manual sheet cannot do quickly: it is read off the Action Priority
 * levers, so it states what the recommended action actually achieves
 * rather than an estimate of it.
 */
export function DfmeaSheet({
  result,
  approved = false,
  systemPackage = "",
  collapsed = false,
  onSubmitted,
}: {
  result: SheetResult;
  approved?: boolean;
  systemPackage?: string;
  /** Header and submit only - the full table is shown on its own tab. */
  collapsed?: boolean;
  onSubmitted?: (draftIds: string[]) => void;
}) {
  const [showEvidence, setShowEvidence] = useState(true);
  const [submit, setSubmit] = useState<
    | { status: "idle" }
    | { status: "sending" }
    | { status: "sent"; draftIds: string[] }
    | { status: "failed"; message: string }
  >({ status: "idle" });

  // One draft per part, sharing a package reference. Quality reviews each
  // part on its own merits, but can still see they arrived together.
  async function sendToQuality() {
    setSubmit({ status: "sending" });
    const packageRef =
      result.items.length > 1 ? `PKG-${Date.now().toString(36).toUpperCase()}` : "";
    try {
      const ids: string[] = [];
      for (const block of result.items) {
        if (block.status !== "success") continue;
        const first = block.rows[0];
        const { draft_id } = await api.submitDraft({
          part_number: block.part_number,
          part_name: block.item_interface ?? "",
          function: first?.elementary_function ?? "",
          material: first?.material ?? "",
          system_package: first?.system_package || systemPackage,
          part_type_name: block.part_type_name ?? "",
          package_ref: packageRef,
          // Sent whole, not summarised: Quality should review the document
          // the engineer reviewed, with the provenance intact.
          accepted_rows: block.rows as unknown as Record<string, unknown>[],
          declined_rows: (block.declined ?? []) as unknown as Record<string, unknown>[],
        });
        ids.push(draft_id);
      }
      setSubmit({ status: "sent", draftIds: ids });
      onSubmitted?.(ids);
    } catch (err) {
      setSubmit({
        status: "failed",
        message: err instanceof ApiError ? err.message : "Could not reach the API.",
      });
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <Card className="px-5 py-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h3 className="font-display text-[15px] font-semibold text-ink">
              {approved ? "DFMEA report" : "Draft DFMEA"} — {result.total_rows} rows
              across {result.items.length} part
              {result.items.length === 1 ? "" : "s"}
              {approved ? (
                <span className="ml-2 rounded-full bg-ok-soft px-2 py-0.5 align-middle font-mono text-[9.5px] uppercase tracking-wide text-ok">
                  engineer reviewed
                </span>
              ) : null}
            </h3>
            <p className="mt-1 max-w-[80ch] text-xs leading-relaxed text-ink-faint">
              {result.high_rows} High priority · {result.safety_rows} at
              severity 9+ · {result.rows_with_evidence} of {result.total_rows}{" "}
              rows carry a warranty record. Occurrence is measured from claims,
              not estimated. Responsibility and target dates are left blank on
              purpose — those are yours to commit to.
            </p>
          </div>
          <div className="flex shrink-0 gap-2">
            {collapsed ? null : (
              <Button onClick={() => setShowEvidence((v) => !v)}>
                {showEvidence ? "Hide evidence columns" : "Show evidence columns"}
              </Button>
            )}
            <Button onClick={() => downloadCsv(result)}>⬇ Export CSV</Button>
            {approved && submit.status !== "sent" ? (
              <Button
                variant="primary"
                onClick={sendToQuality}
                disabled={submit.status === "sending"}
              >
                {submit.status === "sending"
                  ? "Sending…"
                  : "\u{1F4E4} Send to Quality Review"}
              </Button>
            ) : null}
          </div>
        </div>

        {submit.status === "sent" ? (
          <div className="mt-3">
            <Callout tone="ok">
              Sent to Quality as{" "}
              <strong>{submit.draftIds.join(", ")}</strong>. Open the Quality
              Engineer tab to review it — the row sources, override reasons and
              declined rows travel with it.
            </Callout>
          </div>
        ) : null}
        {submit.status === "failed" ? (
          <div className="mt-3">
            <Callout tone="crit">{submit.message}</Callout>
          </div>
        ) : null}
        {!result.ap_table_verified ? (
          <div className="mt-3">
            <Callout tone="warn">
              Action Priority is provisional — the DFMEA AP table is not yet
              fully verified against the published AIAG-VDA handbook, so the
              legacy RPN column is kept alongside it.
            </Callout>
          </div>
        ) : null}
      </Card>

      {collapsed
        ? null
        : result.items.map((block, i) => (
            <ItemBlock
              key={`${block.part_number}-${i}`}
              block={block}
              showEvidence={showEvidence}
              approved={approved}
            />
          ))}
    </div>
  );
}

function ItemBlock({
  block,
  showEvidence,
  approved,
}: {
  block: SheetItemBlock;
  showEvidence: boolean;
  approved: boolean;
}) {
  if (block.status !== "success") {
    return (
      <Callout tone="warn">
        <strong>{block.part_number || "(no part number)"}</strong> —{" "}
        {block.reason ?? "No failure modes could be proposed."}
      </Callout>
    );
  }

  return (
    <Card className="px-5 py-4">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="font-mono text-sm font-semibold text-accent">
          {block.part_number || "(no part number)"}
        </span>
        <span className="font-display text-[15px] font-semibold text-ink">
          {block.item_interface}
        </span>
        <span className="text-xs text-ink-faint">
          identified as {block.part_type_name}
          {block.confirmed
            ? " (confirmed)"
            : ` (${Math.round((block.confidence ?? 0) * 100)}% of the neighbour vote)`}
        </span>
      </div>

      {!block.confirmed && !block.confident ? (
        <p className="mt-1.5 max-w-[85ch] text-xs leading-relaxed text-warn">
          {block.type_reason}
        </p>
      ) : null}

      {block.similar_parts && block.similar_parts.length > 0 ? (
        <p className="mt-2 text-xs text-ink-soft">
          <span className="font-semibold">Similar parts already built:</span>{" "}
          {block.similar_parts.map((n, i) => (
            <span key={n.part_id}>
              {i > 0 ? " · " : ""}
              {n.item_reference}{" "}
              <span className="font-mono text-ink-faint">({n.part_id})</span>
            </span>
          ))}
        </p>
      ) : null}

      {block.own_history && block.own_history.length > 0 ? (
        <p className="mt-1.5 text-xs text-crit">
          <span className="font-semibold">
            This part already has {block.own_history.length} warranty issue
            {block.own_history.length === 1 ? "" : "s"} on record:
          </span>{" "}
          {block.own_history.slice(0, 4).map((h, i) => (
            <span key={h.issue_id}>
              {i > 0 ? " · " : ""}
              <span className="font-mono">{h.issue_id}</span>{" "}
              {h.report_date?.slice(0, 10)}
            </span>
          ))}
        </p>
      ) : null}

      {block.declined && block.declined.length > 0 ? (
        <div className="mt-2.5">
          <Callout tone="warn">
            <strong className="block pb-1">
              {block.declined.length} row(s) considered and left out by the
              engineer — recorded, not missing:
            </strong>
            <ul className="flex flex-col gap-0.5">
              {block.declined.map((d, i) => (
                <li key={i}>
                  {d.failure_mode || "(unnamed)"} (S{d.severity}, {d.action_priority})
                  {d.reason ? ` — ${d.reason}` : ""}
                </li>
              ))}
            </ul>
          </Callout>
        </div>
      ) : null}

      <div className="mt-3 overflow-x-auto rounded-[8px] border border-border">
        <table className={`${approved ? "min-w-[2600px]" : "min-w-[2400px]"} border-collapse text-left text-[12px]`}>
          <thead>
            <tr className="border-b border-border bg-bg-elevated font-mono text-[9.5px] uppercase tracking-wide text-ink-faint">
              <Group span={2}>Item &amp; function</Group>
              <Group span={3}>Failure mode &amp; effects</Group>
              <Group span={5}>Failure cause &amp; prevention controls</Group>
              <Group span={3}>Detection controls</Group>
              <Group span={2}>Priority</Group>
              <Group span={4}>Action details</Group>
              <Group span={5}>Reassessment of risk</Group>
              {showEvidence ? <Group span={3}>Evidence</Group> : null}
              {approved ? <Group span={1}>Source</Group> : null}
            </tr>
            <tr className="border-b border-border bg-bg-elevated font-mono text-[9.5px] uppercase tracking-wide text-ink-faint">
              <Th>Item / interface</Th>
              <Th>Elementary function</Th>
              <Th>Potential failure mode</Th>
              <Th>Potential effect(s)</Th>
              <Th num>Sev</Th>
              <Th>Potential cause</Th>
              <Th>Drawing char. / design spec</Th>
              <Th num>PES?</Th>
              <Th>Current design controls (prevention)</Th>
              <Th num>Occ</Th>
              <Th>Current detection control</Th>
              <Th>Test ref.</Th>
              <Th num>Det</Th>
              <Th num>AP</Th>
              <Th num>RPN</Th>
              <Th>Recommended action(s)</Th>
              <Th>Responsibility</Th>
              <Th>Target date</Th>
              <Th>Action taken</Th>
              <Th num>Sev</Th>
              <Th num>Occ</Th>
              <Th num>Det</Th>
              <Th num>AP</Th>
              <Th num>RPN</Th>
              {showEvidence ? (
                <>
                  <Th>Learned from</Th>
                  <Th>8D records</Th>
                  <Th num>Claims/1000</Th>
                </>
              ) : null}
              {approved ? <Th>Row source</Th> : null}
            </tr>
          </thead>
          <tbody>
            {block.rows.map((row) => (
              <SheetTableRow
                key={row.mode_id}
                row={row}
                showEvidence={showEvidence}
                approved={approved}
              />
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function SheetTableRow({
  row,
  showEvidence,
  approved,
}: {
  row: SheetRow;
  showEvidence: boolean;
  approved: boolean;
}) {
  const improved =
    row.reassessed_action_priority !== row.action_priority ||
    row.reassessed_occurrence !== row.occurrence ||
    row.reassessed_detection !== row.detection;

  return (
    <tr className="border-b border-border align-top last:border-none hover:bg-surface-hover">
      <Td>{row.item_interface}</Td>
      <Td>{row.elementary_function}</Td>
      <Td strong>{row.failure_mode}</Td>
      <Td>
        {row.potential_effect}
        <span className="mt-0.5 block font-mono text-[9.5px] text-ink-faint">
          {row.system_level}
        </span>
      </Td>
      <Td num tone={row.severity >= 9 ? "crit" : undefined}>{row.severity}</Td>
      <Td>{row.potential_cause}</Td>
      <Td>{row.drawing_spec}</Td>
      <Td num>{row.pes}</Td>
      <Td>{row.design_control_prevention}</Td>
      <Td num>{row.occurrence}</Td>
      <Td>{row.detection_control}</Td>
      <Td>{row.test_reference || <Blank />}</Td>
      <Td num>{row.detection}</Td>
      <Td num>
        <ApBadge ap={row.action_priority} />
      </Td>
      <Td num>{row.rpn_legacy}</Td>
      <Td>{row.recommended_action}</Td>
      <Td>{row.responsibility || <Blank />}</Td>
      <Td>{row.target_completion_date || <Blank />}</Td>
      <Td>{row.action_taken || <Blank />}</Td>
      <Td num>{row.reassessed_severity}</Td>
      <Td num tone={improved ? "ok" : undefined}>{row.reassessed_occurrence}</Td>
      <Td num tone={improved ? "ok" : undefined}>{row.reassessed_detection}</Td>
      <Td num>
        <ApBadge ap={row.reassessed_action_priority} />
      </Td>
      <Td num>{row.reassessed_rpn}</Td>
      {showEvidence ? (
        <>
          <Td>{row.learned_from}</Td>
          <Td mono>{row.evidence_ids}</Td>
          <Td num>{row.claims_per_1000 ?? "—"}</Td>
        </>
      ) : null}
      {approved ? (
        <Td>
          <ProvenanceTag row={row} />
        </Td>
      ) : null}
    </tr>
  );
}

/** Where a row came from. An unmarked row is one nobody vouched for. */
function ProvenanceTag({ row }: { row: SheetRow }) {
  const label =
    row.provenance === "engineer_added"
      ? "Engineer's own"
      : row.provenance === "edited"
        ? "Evidence, engineer-edited"
        : "Evidence, accepted";
  const tone =
    row.provenance === "engineer_added"
      ? "bg-accent-soft text-accent-strong"
      : row.provenance === "edited"
        ? "bg-warn-soft text-warn"
        : "bg-ok-soft text-ok";
  return (
    <>
      <span
        className={`inline-block rounded-full px-2 py-0.5 font-mono text-[9px] uppercase tracking-wide ${tone}`}
      >
        {label}
      </span>
      {row.occurrence_override_reason ? (
        <span className="mt-1 block text-[10px] leading-snug text-warn">
          Occ override: {row.occurrence_override_reason}
        </span>
      ) : null}
      {row.severity_dispute_note ? (
        <span className="mt-1 block text-[10px] leading-snug text-warn">
          Sev disputed: {row.severity_dispute_note}
        </span>
      ) : null}
    </>
  );
}

function Group({ span, children }: { span: number; children: React.ReactNode }) {
  return (
    <th
      colSpan={span}
      className="border-b border-r border-border px-2 py-1.5 text-center text-[9px] tracking-[0.1em] text-accent-strong last:border-r-0"
    >
      {children}
    </th>
  );
}

function Th({ children, num = false }: { children: React.ReactNode; num?: boolean }) {
  return (
    <th
      className={`border-r border-border px-2 py-2 font-medium last:border-r-0 ${
        num ? "text-center" : ""
      }`}
    >
      {children}
    </th>
  );
}

function Td({
  children,
  num = false,
  mono = false,
  strong = false,
  tone,
}: {
  children: React.ReactNode;
  num?: boolean;
  mono?: boolean;
  strong?: boolean;
  tone?: "crit" | "ok";
}) {
  const toneClass = tone === "crit" ? "text-crit font-semibold" : tone === "ok" ? "text-ok font-semibold" : "";
  return (
    <td
      className={`border-r border-border px-2 py-2 last:border-r-0 ${
        num ? "text-center font-mono whitespace-nowrap" : ""
      } ${mono ? "font-mono text-[10px]" : ""} ${strong ? "font-semibold text-ink" : "text-ink-soft"} ${toneClass}`}
    >
      {children}
    </td>
  );
}

function Blank() {
  return <span className="text-ink-faint">—</span>;
}

const CSV_COLUMNS: { key: keyof SheetRow; label: string }[] = [
  { key: "part_number", label: "Part Number" },
  { key: "item_interface", label: "Item (Element) / Interface" },
  { key: "elementary_function", label: "Elementary Function" },
  { key: "material", label: "Material" },
  { key: "system_package", label: "System Package" },
  { key: "failure_mode", label: "Potential Failure Mode" },
  { key: "potential_effect", label: "Potential Effect(s) of Failure" },
  { key: "system_level", label: "System Level" },
  { key: "severity", label: "Sev" },
  { key: "potential_cause", label: "Potential Cause of Failure" },
  { key: "drawing_spec", label: "Drawing Characteristic / Design Specification" },
  { key: "pes", label: "PES?" },
  { key: "design_control_prevention", label: "Current Design Controls (Prevention)" },
  { key: "occurrence", label: "Occ" },
  { key: "detection_control", label: "Current Detection Control" },
  { key: "test_reference", label: "Test Reference Number" },
  { key: "detection", label: "Det" },
  { key: "action_priority", label: "Action Priority" },
  { key: "rpn_legacy", label: "RPN (legacy)" },
  { key: "recommended_action", label: "Recommended Action(s)" },
  { key: "responsibility", label: "Responsibility" },
  { key: "target_completion_date", label: "Target Completion Date" },
  { key: "action_taken", label: "Action Taken" },
  { key: "completed_date", label: "Completed Date" },
  { key: "reassessed_severity", label: "Reassessed Sev" },
  { key: "reassessed_occurrence", label: "Reassessed Occ" },
  { key: "reassessed_detection", label: "Reassessed Det" },
  { key: "reassessed_action_priority", label: "Reassessed AP" },
  { key: "reassessed_rpn", label: "Reassessed RPN" },
  { key: "reassessment_basis", label: "Basis of Reassessment" },
  { key: "learned_from", label: "Learned From" },
  { key: "evidence_ids", label: "8D / Warranty Records" },
  { key: "field_reports", label: "Field Reports" },
  { key: "field_claims", label: "Field Claims" },
  { key: "claims_per_1000", label: "Claims per 1000 Units" },
  { key: "scope_level", label: "Inheritance Level" },
  { key: "provenance", label: "Row Source" },
  { key: "occurrence_override_reason", label: "Occurrence Override Reason" },
  { key: "severity_dispute_note", label: "Severity Dispute Note" },
];

function csvCell(value: unknown): string {
  const s = value === null || value === undefined ? "" : String(value);
  // Quote if the value could otherwise break the row, and double any
  // embedded quotes - the plain CSV escaping rule.
  return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

function downloadCsv(result: SheetResult) {
  const rows = result.items.flatMap((item) => item.rows);
  const lines = [
    CSV_COLUMNS.map((c) => csvCell(c.label)).join(","),
    ...rows.map((row) => CSV_COLUMNS.map((c) => csvCell(row[c.key])).join(",")),
  ];
  // BOM so Excel opens the UTF-8 correctly on a Windows machine, which is
  // where these sheets actually get opened.
  const blob = new Blob(["﻿" + lines.join("\r\n")], {
    type: "text/csv;charset=utf-8;",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  const stamp = new Date().toISOString().slice(0, 10);
  a.download = `mechnari-dfmea-${stamp}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

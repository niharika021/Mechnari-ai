"use client";

import { useState } from "react";
import { api, ApiError, type CandidateRow, type PartType, type Proposal } from "@/lib/api";
import { ApBadge, Button, Callout, Card, Field, Select, Spinner, TextArea, TextInput } from "@/components/ui";

export function DesignEngineerForm({
  partTypes,
  systemPackages,
}: {
  partTypes: PartType[];
  systemPackages: string[];
}) {
  const [partName, setPartName] = useState("New EPDM Fuel Return Line");
  const [material, setMaterial] = useState("EPDM rubber with textile braid");
  const [func, setFunc] = useState(
    "Return unburnt diesel from the injector rail to the tank",
  );
  const [partTypeId, setPartTypeId] = useState("");
  const [systemPackage, setSystemPackage] = useState(systemPackages[0] ?? "");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [accepted, setAccepted] = useState<Record<string, boolean>>({});
  const [submitState, setSubmitState] = useState<
    { status: "idle" } | { status: "submitting" } | { status: "done"; draftId: string }
  >({ status: "idle" });

  async function handleIdentify(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSubmitState({ status: "idle" });
    try {
      const result = await api.proposeDfmea({
        part_name: partName,
        function: func,
        material,
        part_type_id: partTypeId,
      });
      setProposal(result);
      if (result.status === "success") {
        const initial: Record<string, boolean> = {};
        for (const row of result.candidates) initial[row.mode_id] = true;
        setAccepted(initial);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reach the API.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmitDraft() {
    if (proposal?.status !== "success") return;
    setSubmitState({ status: "submitting" });
    const acceptedRows = proposal.candidates.filter((r) => accepted[r.mode_id]);
    const declinedRows = proposal.candidates.filter((r) => !accepted[r.mode_id]);
    try {
      const { draft_id } = await api.submitDraft({
        part_name: partName,
        function: func,
        material,
        system_package: systemPackage,
        part_type_name: proposal.part_type_name,
        accepted_rows: acceptedRows,
        declined_rows: declinedRows,
      });
      setSubmitState({ status: "done", draftId: draft_id });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not submit the draft.");
      setSubmitState({ status: "idle" });
    }
  }

  const candidates = proposal?.status === "success" ? proposal.candidates : [];
  const acceptedCount = candidates.filter((r) => accepted[r.mode_id]).length;
  const declinedHigh = candidates.filter(
    (r) => !accepted[r.mode_id] && r.action_priority === "H",
  );

  return (
    <div className="mt-5 flex flex-col gap-6">
      <Card className="px-5 pb-3 pt-4.5">
        <form onSubmit={handleIdentify} className="flex flex-col gap-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Component name">
              <TextInput value={partName} onChange={(e) => setPartName(e.target.value)} required />
            </Field>
            <Field label="Material / compound">
              <TextInput value={material} onChange={(e) => setMaterial(e.target.value)} required />
            </Field>
          </div>
          <Field label="Elementary function">
            <TextArea
              value={func}
              onChange={(e) => setFunc(e.target.value)}
              rows={3}
              required
            />
          </Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Confirm part type (optional)">
              <Select value={partTypeId} onChange={(e) => setPartTypeId(e.target.value)}>
                <option value="">(let retrieval suggest)</option>
                {partTypes
                  .slice()
                  .sort((a, b) => a.part_type_name.localeCompare(b.part_type_name))
                  .map((pt) => (
                    <option key={pt.part_type_id} value={pt.part_type_id}>
                      {pt.part_type_name}
                    </option>
                  ))}
              </Select>
            </Field>
            <Field label="System package (for your own record)">
              <Select value={systemPackage} onChange={(e) => setSystemPackage(e.target.value)}>
                {systemPackages.map((pkg) => (
                  <option key={pkg} value={pkg}>
                    {pkg}
                  </option>
                ))}
              </Select>
            </Field>
          </div>
          <Button type="submit" variant="primary" disabled={loading} className="w-fit">
            {loading ? "Identifying…" : "\u{1F50D} Identify & Draft DFMEA"}
          </Button>
        </form>
      </Card>

      {loading ? <Spinner /> : null}
      {error ? <Callout tone="crit">{error}</Callout> : null}

      {proposal && proposal.status !== "success" ? (
        <Callout tone="warn">{proposal.reason}</Callout>
      ) : null}

      {proposal?.status === "success" ? (
        <>
          <Callout tone={proposal.confirmed || proposal.confident ? "ok" : "warn"}>
            {proposal.confirmed ? (
              <>
                Part type confirmed as <strong>{proposal.part_type_name}</strong>.
              </>
            ) : (
              <>
                Suggested part type: <strong>{proposal.part_type_name}</strong>{" "}
                ({Math.round(proposal.confidence * 100)}% of the neighbour vote).{" "}
                {proposal.reason}
              </>
            )}
          </Callout>

          {proposal.neighbours.length > 0 ? (
            <p className="text-[13px] text-ink-soft">
              Closest historical parts:{" "}
              {proposal.neighbours.slice(0, 4).map((n, i) => (
                <span key={n.part_id}>
                  {i > 0 ? "  ·  " : ""}
                  <span className="font-mono text-accent">{n.similarity.toFixed(3)}</span>{" "}
                  {n.part_id} ({n.item_reference})
                </span>
              ))}
            </p>
          ) : null}

          <div>
            <h3 className="font-display text-[15px] font-semibold text-ink">
              Draft DFMEA — {candidates.length} candidate rows from company history
            </h3>
            <p className="mt-1 text-xs text-ink-faint">
              Uncheck a row to leave it out of the draft. High rows show what single
              change - Occurrence or Detection, computed against the real AP table,
              not invented - would bring the priority down.
            </p>
          </div>

          <div className="flex flex-col gap-3">
            {candidates.map((row) => (
              <CandidateCard
                key={row.mode_id}
                row={row}
                checked={accepted[row.mode_id] ?? true}
                onToggle={(v) =>
                  setAccepted((prev) => ({ ...prev, [row.mode_id]: v }))
                }
              />
            ))}
          </div>

          {declinedHigh.length > 0 ? (
            <Callout tone="warn">
              {declinedHigh.length} declined row(s) are High priority - Quality will
              see these were considered and left out, not missed.
            </Callout>
          ) : null}

          <div className="flex items-center justify-between border-t border-border pt-4">
            <span className="text-[13px] text-ink-faint">
              {acceptedCount} of {candidates.length} candidate rows included in the draft.
            </span>
            {submitState.status === "done" ? (
              <Callout tone="ok">
                Submitted as <strong>{submitState.draftId}</strong>. Open the Quality
                Engineer tab to see it in the queue.
              </Callout>
            ) : (
              <Button
                variant="primary"
                onClick={handleSubmitDraft}
                disabled={submitState.status === "submitting" || candidates.length === 0}
              >
                {submitState.status === "submitting"
                  ? "Submitting…"
                  : "\u{1F4E4} Send Draft to Quality Review"}
              </Button>
            )}
          </div>
        </>
      ) : null}
    </div>
  );
}

function CandidateCard({
  row,
  checked,
  onToggle,
}: {
  row: CandidateRow;
  checked: boolean;
  onToggle: (v: boolean) => void;
}) {
  const [open, setOpen] = useState(row.action_priority === "H");
  const levers = row.levers ?? [];

  return (
    <Card className="overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-surface-hover"
      >
        <input
          type="checkbox"
          checked={checked}
          onClick={(e) => e.stopPropagation()}
          onChange={(e) => onToggle(e.target.checked)}
          className="h-4 w-4 accent-accent"
        />
        <span className="flex-1 text-sm font-semibold text-ink">{row.failure_mode}</span>
        <span className="font-mono text-xs text-ink-soft">
          S{row.severity} O{row.occurrence} D{row.detection}
        </span>
        <ApBadge ap={row.action_priority} />
      </button>
      {open ? (
        <div className="border-t border-border px-4 py-3.5 text-sm">
          <dl className="flex flex-col gap-1.5">
            <Detail label="Potential cause" value={row.potential_cause} />
            <Detail label="Effect" value={row.effect_description} />
            <Detail label="Learned from" value={row.learned_from} />
            <Detail label="Evidence" value={row.evidence_ids} mono />
            <Detail label="Recommended action" value={row.recommended_action} />
          </dl>
          {row.action_priority !== "L" ? (
            <div className="mt-3">
              {levers.length > 0 ? (
                <Callout tone="accent">
                  <strong className="block pb-1">What would bring this down</strong>
                  <ul className="flex flex-col gap-0.5">
                    {levers.map((lever, i) => (
                      <li key={i}>
                        Improving <strong className="capitalize">{lever.factor}</strong> from{" "}
                        {lever.from} to {lever.to} would move this to{" "}
                        <strong>{lever.resulting_ap}</strong>.
                      </li>
                    ))}
                  </ul>
                </Callout>
              ) : (
                <p className="text-xs text-ink-faint">
                  No single-factor change in Occurrence or Detection alone moves this
                  below {row.action_priority} at the current Severity - both would need
                  to improve together, or the effect itself needs to change.
                </p>
              )}
            </div>
          ) : null}
        </div>
      ) : null}
    </Card>
  );
}

function Detail({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex gap-2">
      <dt className="w-36 shrink-0 font-semibold text-ink-soft">{label}</dt>
      <dd className={mono ? "font-mono text-xs text-ink-soft" : "text-ink"}>{value}</dd>
    </div>
  );
}

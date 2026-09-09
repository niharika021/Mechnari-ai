"use client";

import { useState } from "react";
import {
  api,
  ApiError,
  type ExistingDfmea,
  type Part,
  type PartType,
  type SheetItemInput,
  type SheetResult,
} from "@/lib/api";
import { ExistingDfmeaView } from "@/components/ExistingDfmeaView";
import {
  DfmeaReview,
  toReviewState,
  type ReviewState,
} from "@/components/DfmeaReview";
import {
  Button,
  Callout,
  Card,
  Field,
  Select,
  Spinner,
  TextArea,
  TextInput,
} from "@/components/ui";
import { DfmeaSheet } from "@/components/DfmeaSheet";

type Row = {
  key: number;
  part_number: string;
  description: string;
  function: string;
  material: string;
  part_type_id: string;
};

let nextKey = 1;
function blankRow(): Row {
  return {
    key: nextKey++,
    part_number: "",
    description: "",
    function: "",
    material: "",
    part_type_id: "",
  };
}

const EXAMPLE: Omit<Row, "key"> = {
  part_number: "EXAMPLE-0001",
  description: "EPDM Fuel Return Line",
  function: "Return unburnt diesel from the injector rail to the tank",
  material: "EPDM rubber with textile braid",
  part_type_id: "",
};

type Mode = "single" | "package" | "existing";

/**
 * The engineer's approved review, turned back into a sheet.
 *
 * Only included rows survive, and each one carries how it got there -
 * from the evidence, from an edit, or from the engineer's own assessment -
 * along with any reason given for overriding a warranty-measured
 * Occurrence or disputing a registry Severity. That provenance is the
 * audit trail a manual sheet does not have.
 *
 * Declined rows are not discarded silently: they are counted here and
 * carried with their reasons, which is what Quality needs to see the
 * difference between "considered and rejected" and "never looked at".
 */
function approvedSheet(states: ReviewState[]): SheetResult {
  const items = states.map((state) => {
    const included = state.rows.filter((r) => r.include);
    return {
      status: "success" as const,
      part_number: state.partNumber,
      item_interface: state.itemInterface,
      part_type_name: state.partTypeName,
      confirmed: true,
      rows: included.map((r) => ({
        ...r,
        provenance: r.provenance,
        occurrence_override_reason: r.occurrence_override_reason,
        severity_dispute_note: r.severity_disputed ? r.severity_dispute_note : "",
      })),
      declined: state.rows
        .filter((r) => !r.include)
        .map((r) => ({
          failure_mode: r.failure_mode,
          action_priority: r.action_priority,
          severity: r.severity,
          reason: r.decline_reason,
        })),
    };
  });
  const all = items.flatMap((i) => i.rows);
  return {
    items,
    total_rows: all.length,
    high_rows: all.filter((r) => r.action_priority === "H").length,
    safety_rows: all.filter((r) => r.severity >= 9).length,
    rows_with_evidence: all.filter((r) => r.evidence_ids).length,
    ap_table_verified: false,
  };
}

export function PartIntake({
  partTypes,
  systemPackages,
  parts,
}: {
  partTypes: PartType[];
  systemPackages: string[];
  parts: Part[];
}) {
  // A package is the same operation repeated, so it is one mode switch
  // rather than two different forms. "existing" is genuinely different:
  // it reads the DFMEA already on file instead of drafting a new one.
  const [mode, setMode] = useState<Mode>("single");
  const [systemPackage, setSystemPackage] = useState(systemPackages[0] ?? "");
  const [rows, setRows] = useState<Row[]>([{ ...EXAMPLE, key: nextKey++ }]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Three stages, not one: findings -> the engineer's review -> the
  // report. The middle one is the point. Nothing reaches a DFMEA that an
  // engineer has not passed judgement on.
  const [review, setReview] = useState<ReviewState[] | null>(null);
  const [found, setFound] = useState<SheetResult | null>(null);
  const [result, setResult] = useState<SheetResult | null>(null);

  const [existingPartId, setExistingPartId] = useState(parts[0]?.part_id ?? "");
  const [existing, setExisting] = useState<ExistingDfmea | null>(null);

  const sortedTypes = [...partTypes].sort((a, b) =>
    a.part_type_name.localeCompare(b.part_type_name),
  );

  function update(key: number, patch: Partial<Row>) {
    setRows((prev) => prev.map((r) => (r.key === key ? { ...r, ...patch } : r)));
  }

  function switchMode(next: Mode) {
    setMode(next);
    setResult(null);
    setReview(null);
    setExisting(null);
    setError(null);
    if (next === "single") setRows((prev) => prev.slice(0, 1));
  }

  async function loadExisting(e: React.FormEvent) {
    e.preventDefault();
    if (!existingPartId) return;
    setLoading(true);
    setError(null);
    setExisting(null);
    try {
      setExisting(await api.existingDfmea(existingPartId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reach the API.");
    } finally {
      setLoading(false);
    }
  }

  const describable = rows.filter(
    (r) => r.description.trim() || r.function.trim() || r.material.trim(),
  );

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (describable.length === 0) {
      setError("Describe at least one part - a description, function or material.");
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    setReview(null);
    try {
      const items: SheetItemInput[] = describable.map((r) => ({
        part_number: r.part_number,
        description: r.description,
        function: r.function,
        material: r.material,
        system_package: systemPackage,
        part_type_id: r.part_type_id,
      }));
      const found = await api.dfmeaSheet(items);
      const states = toReviewState(found);
      if (states.length === 0) {
        // Nothing identifiable - show the reasons rather than an empty review.
        setResult(found);
      } else {
        setFound(found);
        setReview(states);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reach the API.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mt-5 flex flex-col gap-6">
      <Card className="px-5 pb-4 pt-4">
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <div className="flex gap-1 rounded-[9px] border border-border bg-bg-elevated p-1">
            <ModeButton active={mode === "single"} onClick={() => switchMode("single")}>
              Single part
            </ModeButton>
            <ModeButton active={mode === "package"} onClick={() => switchMode("package")}>
              Package / assembly
            </ModeButton>
            <ModeButton active={mode === "existing"} onClick={() => switchMode("existing")}>
              Existing part on file
            </ModeButton>
          </div>
          <p className="text-xs text-ink-faint">
            {mode === "single"
              ? "One new part."
              : mode === "package"
                ? `A package of parts analysed together - ${rows.length} in the list.`
                : "Read the DFMEA already on file for a part, and what is missing from it."}
          </p>
        </div>

        {mode === "existing" ? (
          <form onSubmit={loadExisting} className="flex flex-col gap-4">
            <Field label="Part already on file">
              <Select
                value={existingPartId}
                onChange={(e) => setExistingPartId(e.target.value)}
              >
                {[...parts]
                  .sort((a, b) => a.part_id.localeCompare(b.part_id))
                  .map((p) => (
                    <option key={p.part_id} value={p.part_id}>
                      {p.part_id} — {p.item_reference}
                    </option>
                  ))}
              </Select>
            </Field>
            <Button type="submit" variant="primary" disabled={loading} className="w-fit">
              {loading ? "Loading…" : "\u{1F4C4} Open the DFMEA on file"}
            </Button>
          </form>
        ) : (
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <Field label="System package this belongs to">
            <Select
              value={systemPackage}
              onChange={(e) => setSystemPackage(e.target.value)}
            >
              {systemPackages.map((pkg) => (
                <option key={pkg} value={pkg}>
                  {pkg}
                </option>
              ))}
            </Select>
          </Field>

          <div className="flex flex-col gap-4">
            {rows.map((row, i) => (
              <div
                key={row.key}
                className={
                  mode === "package"
                    ? "rounded-[9px] border border-border bg-bg-elevated px-4 py-3.5"
                    : ""
                }
              >
                {mode === "package" ? (
                  <div className="mb-2.5 flex items-center justify-between">
                    <span className="font-mono text-[10.5px] uppercase tracking-wider text-ink-faint">
                      Part {i + 1} of {rows.length}
                    </span>
                    {rows.length > 1 ? (
                      <button
                        type="button"
                        onClick={() =>
                          setRows((prev) => prev.filter((r) => r.key !== row.key))
                        }
                        className="text-xs font-semibold text-crit hover:opacity-70"
                      >
                        Remove
                      </button>
                    ) : null}
                  </div>
                ) : null}

                <div className="grid gap-4 sm:grid-cols-2">
                  <Field label="Part number">
                    <TextInput
                      value={row.part_number}
                      onChange={(e) => update(row.key, { part_number: e.target.value })}
                      placeholder="e.g. EXAMPLE-0001"
                    />
                  </Field>
                  <Field label="Part description">
                    <TextInput
                      value={row.description}
                      onChange={(e) => update(row.key, { description: e.target.value })}
                      placeholder="e.g. EPDM Fuel Return Line"
                    />
                  </Field>
                </div>

                <div className="mt-4">
                  <Field label="Elementary function">
                    <TextArea
                      value={row.function}
                      onChange={(e) => update(row.key, { function: e.target.value })}
                      rows={2}
                      placeholder="What this part has to do"
                    />
                  </Field>
                </div>

                <div className="mt-4 grid gap-4 sm:grid-cols-2">
                  <Field label="Material / compound">
                    <TextInput
                      value={row.material}
                      onChange={(e) => update(row.key, { material: e.target.value })}
                      placeholder="e.g. EPDM rubber with textile braid"
                    />
                  </Field>
                  <Field label="Confirm part type (optional)">
                    <Select
                      value={row.part_type_id}
                      onChange={(e) => update(row.key, { part_type_id: e.target.value })}
                    >
                      <option value="">(let retrieval suggest)</option>
                      {sortedTypes.map((pt) => (
                        <option key={pt.part_type_id} value={pt.part_type_id}>
                          {pt.part_type_name}
                        </option>
                      ))}
                    </Select>
                  </Field>
                </div>
              </div>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {mode === "package" ? (
              <Button
                type="button"
                onClick={() => setRows((prev) => [...prev, blankRow()])}
                disabled={rows.length >= 25}
              >
                + Add another part
              </Button>
            ) : null}
            <Button type="submit" variant="primary" disabled={loading}>
              {loading
                ? "Building the DFMEA…"
                : `\u{1F50D} Build DFMEA${
                    mode === "package" && describable.length > 1
                      ? ` for ${describable.length} parts`
                      : ""
                  }`}
            </Button>
          </div>
        </form>
        )}
      </Card>

      {loading ? <Spinner /> : null}
      {error ? <Callout tone="crit">{error}</Callout> : null}
      {review ? (
        <DfmeaReview
          initial={review}
          onBack={() => setReview(null)}
          onGenerate={(states) => {
            setReview(null);
            setResult(approvedSheet(states));
          }}
        />
      ) : null}
      {result ? (
        <DfmeaSheet
          result={result}
          approved={!!found}
          systemPackage={systemPackage}
        />
      ) : null}
      {existing ? <ExistingDfmeaView data={existing} /> : null}
    </div>
  );
}

function ModeButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-[7px] px-3.5 py-2 text-sm font-semibold transition-colors ${
        active ? "bg-accent-soft text-accent-strong" : "text-ink-soft hover:text-ink"
      }`}
    >
      {children}
    </button>
  );
}

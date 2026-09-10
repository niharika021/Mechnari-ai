"use client";

import { useEffect, useState } from "react";
import { IconChevronDown, IconDocument, IconRun } from "@/components/icons";
import { useRouter } from "next/navigation";
import {
  api,
  ApiError,
  type ExistingDfmea,
  type Part,
  type PartType,
  type OwnFailureRecord,
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
import { MyReports } from "@/components/MyReports";
import {
  createReport,
  listAll,
  removeReport,
  storageAvailable,
  type AnyReportSummary,
} from "@/lib/reportStore";
import { useAuth } from "@/lib/auth";
import { CopilotActions, type IntakeFields } from "@/components/CopilotActions";
import { OwnRecords } from "@/components/OwnRecords";

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
  const router = useRouter();
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

  const [reanalysing, setReanalysing] = useState(false);

  // Failure records the engineer supplies themselves - see OwnRecords.tsx.
  const [ownRecords, setOwnRecords] = useState<OwnFailureRecord[]>([]);

  // The engineer's own reports, kept in this browser. A package DFMEA is a
  // week of work, so assuming one browser session was wrong.
  const { user } = useAuth();
  const [reports, setReports] = useState<AnyReportSummary[]>([]);
  const [storageOk, setStorageOk] = useState(true);
  const [reportId, setReportId] = useState<string | null>(null);

  useEffect(() => {
    setStorageOk(storageAvailable());
    let cancelled = false;
    listAll(Boolean(user)).then((list) => {
      if (!cancelled) setReports(list);
    });
    return () => {
      cancelled = true;
    };
    // Re-listed on sign-in/out: the server's reports appear or disappear.
  }, [user]);

  function openStored(id: string) {
    router.push(`/design/report/${id}`);
  }

  async function removeStored(id: string) {
    const summary = reports.find((r) => r.id === id);
    await removeReport(id, Boolean(summary?.remote));
    setReports(await listAll(Boolean(user)));
  }

  /**
   * The engineer corrected the part type. Re-run that part with the type
   * confirmed, and splice the fresh findings in place.
   *
   * Only the corrected part is re-run: in a package the other parts were
   * identified independently and re-running them would discard review work
   * for no reason.
   */
  async function reanalyse(partNumber: string, partTypeId: string) {
    const source = describable.find((r) => r.part_number === partNumber);
    if (!source) return;
    setReanalysing(true);
    setError(null);
    try {
      const fresh = await api.dfmeaSheet([{
        part_number: source.part_number,
        description: source.description,
        function: source.function,
        material: source.material,
        system_package: systemPackage,
        part_type_id: partTypeId,
      }]);
      const [replacement] = toReviewState(fresh);
      if (!replacement) {
        setError("That part type produced no applicable failure modes.");
        return;
      }
      setReview((prev) =>
        prev
          ? prev.map((s) => (s.partNumber === partNumber ? replacement : s))
          : prev,
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reach the API.");
    } finally {
      setReanalysing(false);
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
      // Supplied records ride on the first described part. In package
      // mode they would otherwise be duplicated onto every item, which
      // would put the same failure on ten sheets - a single observation
      // about one part, counted ten times.
      const complete = ownRecords.filter(
        (r) => r.failure_mode.trim() && r.effect_id && r.detection_stage,
      );
      const items: SheetItemInput[] = describable.map((r, index) => ({
        part_number: r.part_number,
        description: r.description,
        function: r.function,
        material: r.material,
        system_package: systemPackage,
        part_type_id: r.part_type_id,
        own_records: index === 0 ? complete : [],
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

  /**
   * What the copilot may do here.
   *
   * These reuse the same functions the buttons call, so an agent-driven
   * build is the identical code path as a clicked one - there is no
   * second, less-tested route through the app for the agent to take.
   */
  const firstRow = rows[0];
  const copilotHandlers = {
    fillIntake: (fields: IntakeFields) => {
      if (!firstRow) return;
      update(firstRow.key, {
        ...(fields.part_number !== undefined
          ? { part_number: fields.part_number }
          : {}),
        ...(fields.description !== undefined
          ? { description: fields.description }
          : {}),
        ...(fields.function !== undefined ? { function: fields.function } : {}),
        ...(fields.material !== undefined ? { material: fields.material } : {}),
      });
      if (fields.system_package && systemPackages.includes(fields.system_package)) {
        setSystemPackage(fields.system_package);
      }
    },
    build: () => {
      // Same submit the button runs; the synthetic event only exists
      // because handleSubmit takes one to preventDefault.
      void handleSubmit({ preventDefault: () => {} } as React.FormEvent);
    },
    reanalyseAs: (partTypeName: string) => {
      const match = partTypes.find(
        (pt) =>
          pt.part_type_name.toLowerCase() === partTypeName.toLowerCase().trim() ||
          pt.part_type_name.toLowerCase().includes(partTypeName.toLowerCase().trim()),
      );
      if (!match || !review?.[0]) return false;
      void reanalyse(review[0].partNumber, match.part_type_id);
      return true;
    },
    openExisting: (partIdOrName: string) => {
      const needle = partIdOrName.toLowerCase().trim();
      const match = parts.find(
        (p) =>
          p.part_id.toLowerCase() === needle ||
          p.item_reference.toLowerCase().includes(needle),
      );
      if (!match) return false;
      switchMode("existing");
      setExistingPartId(match.part_id);
      void api.existingDfmea(match.part_id).then(setExisting).catch(() => {
        setError("Could not load that part's DFMEA.");
      });
      return true;
    },
    declineRow: (modeId: string, reason: string) => {
      if (!review) return false;
      let found = false;
      setReview((prev) =>
        prev
          ? prev.map((state) => ({
              ...state,
              rows: state.rows.map((r) => {
                if (r.mode_id !== modeId) return r;
                found = true;
                return { ...r, include: false, decline_reason: reason };
              }),
            }))
          : prev,
      );
      return found;
    },
    context: {
      stage: review ? "reviewing findings" : mode === "existing" ? "reading an existing DFMEA" : "entering part details",
      mode,
      system_package: systemPackage,
      intake: firstRow
        ? {
            part_number: firstRow.part_number,
            description: firstRow.description,
            function: firstRow.function,
            material: firstRow.material,
          }
        : null,
      findings: review?.[0]
        ? {
            identified_as: review[0].partTypeName,
            confidence: review[0].confidence,
            rows: review[0].rows.map((r) => ({
              mode_id: r.mode_id,
              failure_mode: r.failure_mode,
              severity: r.severity,
              occurrence: r.occurrence,
              detection: r.detection,
              action_priority: r.action_priority,
              included: r.include,
              evidence_ids: r.evidence_ids,
            })),
          }
        : null,
    },
  };

  return (
    <div className="mt-5 flex flex-col gap-6">
      <CopilotActions handlers={copilotHandlers} />

      {/*
        Order is the point here, and it took a measurement to get right.

        Removing the marketing hero was supposed to bring the first form
        control up from 620px on a 698px viewport. It did not: the header
        shrank to 53px, and the control stayed at 620, because the form
        was third on the page - behind an explanation and behind the list
        of past reports. Deleting the hero just gave that space to the
        two blocks above the form.

        So: the form first, because drafting a DFMEA is the entire reason
        this view exists. Past reports second, where "reopen what I was
        working on" is still one glance away but is not standing in front
        of today's work. The explanation last and collapsed - it answers
        "should I trust this?", asked once by someone evaluating the
        tool, not by an engineer on their fourth draft of the week.
      */}
      <Card className="px-5 pb-4 pt-4">
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <div className="flex gap-1 rounded-md border border-border bg-bg-elevated p-1">
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
              {loading ? "Loading…" : <><IconDocument size={15} /> Open the DFMEA on file</>}
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
                    ? "rounded-md border border-border bg-bg-elevated px-4 py-3.5"
                    : ""
                }
              >
                {mode === "package" ? (
                  <div className="mb-2.5 flex items-center justify-between">
                    <span className="font-mono text-micro uppercase tracking-wider text-ink-faint">
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

          {/* Between the part fields and the Build button, because it is
              part of describing the part - not an afterthought applied to
              the findings. Collapsed by default; most drafts skip it. */}
          <div className="mb-4">
            <OwnRecords records={ownRecords} onChange={setOwnRecords} />
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
              {loading ? (
                "Building the DFMEA…"
              ) : (
                <>
                  <IconRun size={15} />
                  Build DFMEA
                  {mode === "package" && describable.length > 1
                    ? ` for ${describable.length} parts`
                    : ""}
                </>
              )}
            </Button>
          </div>
        </form>
        )}
      </Card>

      <MyReports
        reports={reports}
        storageOk={storageOk}
        onOpen={openStored}
        onDelete={removeStored}
      />

      {/* Native <details>, not state: it works before hydration, is
          keyboard-operable and announced to screen readers for free, and
          the browser deliberately remembers nothing between loads -
          which is right for something read once. */}
      <details className="group rounded-lg border border-border bg-panel">
        <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-2.5 text-sm font-semibold text-ink-soft hover:text-ink">
          <IconChevronDown
            size={14}
            className="shrink-0 -rotate-90 transition-transform group-open:rotate-0"
          />
          How this works
        </summary>
        <p className="max-w-[76ch] border-t border-border px-4 py-3 text-sm leading-relaxed text-ink-soft">
          Mechnari works out what kind of part each one is, finds what the
          company has already built like it, pulls what actually went wrong
          from the warranty record, and lays the result out in the AIAG-VDA
          form sheet — an 8D reference on every row, Occurrence measured from
          real claims rather than estimated, and the reassessed risk each
          recommended action would actually achieve.
        </p>
      </details>

      {loading ? <Spinner /> : null}
      {error ? <Callout tone="crit">{error}</Callout> : null}
      {review ? (
        <DfmeaReview
          initial={review}
          partTypes={partTypes}
          apTableVerified={found?.ap_table_verified ?? false}
          onReanalyse={reanalyse}
          reanalysing={reanalysing}
          onBack={() => setReview(null)}
          onGenerate={async (states) => {
            const { id } = await createReport(
              approvedSheet(states),
              systemPackage,
              Boolean(user),
            );
            setReview(null);
            // The report has its own address now; the intake form's job is
            // done once it exists.
            router.push(`/design/report/${id}`);
          }}
        />
      ) : null}
      {result ? <DfmeaSheet result={result} systemPackage={systemPackage} /> : null}
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
      className={`rounded-md px-3.5 py-2 text-sm font-semibold transition-colors ${
        active ? "bg-accent-soft text-accent-strong" : "text-ink-soft hover:text-ink"
      }`}
    >
      {children}
    </button>
  );
}

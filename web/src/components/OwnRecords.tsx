"use client";

import { useEffect, useState } from "react";
import {
  api,
  type DetectionStage,
  type FailureEffect,
  type OwnFailureRecord,
} from "@/lib/api";
import { Button, Card, Field, Select, TextInput } from "@/components/ui";
import { IconAlert, IconChevronDown } from "@/components/icons";

/**
 * Failure records the engineer supplies themselves.
 *
 * A designer often knows something the warranty database does not: a
 * failure seen on a prototype, on a previous employer's equivalent part,
 * or in a test that never became an 8D. Without this the only way that
 * knowledge reaches the sheet is as an edit to a row the system happened
 * to propose - which means it never reaches the sheet at all when the
 * system proposes nothing.
 *
 * What this form deliberately does not have is a Severity box. The
 * engineer picks the *effect* from the organisation's registry and the
 * backend looks the severity up. That is the same rule the rest of the
 * product obeys, and putting a severity field here would quietly break
 * the one claim the product rests on: that Severity is a property of the
 * effect rather than of whoever is filling in the form.
 *
 * Occurrence works the same way. Claims and fleet size are optional, and
 * supplying them derives Occurrence through the identical function the
 * warranty path uses. Leaving them blank leaves Occurrence at the floor
 * and the row says "no rate given" - so a guess never ends up looking
 * like a measurement.
 */

const BLANK: OwnFailureRecord = {
  failure_mode: "",
  potential_cause: "",
  effect_id: "",
  detection_stage: "",
  claim_count: null,
  units_in_service: null,
  reference: "",
};

export function OwnRecords({
  records,
  onChange,
}: {
  records: OwnFailureRecord[];
  onChange: (records: OwnFailureRecord[]) => void;
}) {
  const [effects, setEffects] = useState<FailureEffect[]>([]);
  const [stages, setStages] = useState<DetectionStage[]>([]);
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.failureEffects(), api.detectionStages()])
      .then(([e, s]) => {
        if (cancelled) return;
        setEffects(e);
        setStages(s);
      })
      .catch(() => {
        if (!cancelled) setLoadError(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function update(index: number, patch: Partial<OwnFailureRecord>) {
    onChange(records.map((r, i) => (i === index ? { ...r, ...patch } : r)));
  }

  function remove(index: number) {
    onChange(records.filter((_, i) => i !== index));
  }

  // Collapsed by default: most drafts do not need it, and an open form
  // of six fields above the Build button would push the primary action
  // down the page for everyone to serve the minority who use it.
  return (
    <details className="group rounded-lg border border-border bg-panel">
      <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-2.5 text-sm font-semibold text-ink-soft hover:text-ink">
        <IconChevronDown
          size={14}
          className="shrink-0 -rotate-90 transition-transform group-open:rotate-0"
        />
        Add a failure you already know about
        {records.length > 0 ? (
          <span className="ml-1 rounded-full border border-accent-line bg-accent-soft px-2 py-0.5 font-mono text-micro font-semibold text-accent-strong">
            {records.length}
          </span>
        ) : null}
      </summary>

      <div className="border-t border-border px-4 py-3">
        <p className="max-w-[76ch] text-sm text-ink-soft">
          Something seen on a prototype, on an equivalent part at a previous
          employer, or in a test that never became an 8D. It becomes a row on
          the sheet, marked as yours rather than as warranty evidence.
        </p>
        <p className="mt-1.5 max-w-[76ch] text-sm text-ink-faint">
          You choose the <strong>effect</strong>, not the severity — severity
          comes from the organisation&apos;s registry so the same effect scores
          the same on every program. Claims and fleet size are optional; give
          both and Occurrence is measured from them, leave them blank and it
          stays at the floor.
        </p>

        {loadError ? (
          <div className="mt-3 flex items-start gap-2 rounded-md border border-warn-line bg-warn-soft px-3 py-2.5 text-sm text-warn">
            <IconAlert size={15} className="mt-[3px] shrink-0" />
            <span>
              Could not load the effect registry, so a record cannot be scored
              right now. Everything else still works.
            </span>
          </div>
        ) : null}

        <div className="mt-3 flex flex-col gap-3">
          {records.map((record, index) => (
            <Card key={index} tier="sunken" className="px-4 py-3.5">
              <div className="flex flex-col gap-3">
                <Field label="What fails">
                  <TextInput
                    value={record.failure_mode}
                    onChange={(e) =>
                      update(index, { failure_mode: e.target.value })
                    }
                    placeholder="e.g. Quick-connect collar cracks after cold-soak cycling"
                  />
                </Field>

                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="Why it fails (optional)">
                    <TextInput
                      value={record.potential_cause ?? ""}
                      onChange={(e) =>
                        update(index, { potential_cause: e.target.value })
                      }
                      placeholder="e.g. Nylon embrittlement below -30C"
                    />
                  </Field>
                  <Field label="Where you found it">
                    <Select
                      value={record.detection_stage}
                      onChange={(e) =>
                        update(index, { detection_stage: e.target.value })
                      }
                    >
                      <option value="">Select…</option>
                      {stages.map((s) => (
                        <option key={s.stage} value={s.stage}>
                          {s.label} (Detection {s.detection_floor})
                        </option>
                      ))}
                    </Select>
                  </Field>
                </div>

                <Field label="What it causes — sets Severity from the registry">
                  <Select
                    value={record.effect_id}
                    onChange={(e) => update(index, { effect_id: e.target.value })}
                  >
                    <option value="">Select an effect…</option>
                    {effects.map((eff) => (
                      <option key={eff.effect_id} value={eff.effect_id}>
                        {eff.effect_description} — S={eff.standard_severity}
                      </option>
                    ))}
                  </Select>
                </Field>

                <div className="grid gap-3 sm:grid-cols-3">
                  <Field label="Claims (optional)">
                    <TextInput
                      type="number"
                      min={0}
                      value={record.claim_count ?? ""}
                      onChange={(e) =>
                        update(index, {
                          claim_count:
                            e.target.value === "" ? null : Number(e.target.value),
                        })
                      }
                      placeholder="34"
                    />
                  </Field>
                  <Field label="Units in service (optional)">
                    <TextInput
                      type="number"
                      min={0}
                      value={record.units_in_service ?? ""}
                      onChange={(e) =>
                        update(index, {
                          units_in_service:
                            e.target.value === "" ? null : Number(e.target.value),
                        })
                      }
                      placeholder="1200"
                    />
                  </Field>
                  <Field label="Source (optional)">
                    <TextInput
                      value={record.reference ?? ""}
                      onChange={(e) =>
                        update(index, { reference: e.target.value })
                      }
                      placeholder="prototype fleet, winter 2025"
                    />
                  </Field>
                </div>

                <div className="flex justify-end">
                  <button
                    type="button"
                    onClick={() => remove(index)}
                    className="rounded-md px-2 py-1 text-label font-semibold text-ink-faint transition-colors hover:text-crit"
                  >
                    Remove
                  </button>
                </div>
              </div>
            </Card>
          ))}
        </div>

        <Button
          type="button"
          onClick={() => onChange([...records, { ...BLANK }])}
          className="mt-3"
          disabled={loadError}
        >
          + Add a failure record
        </Button>
      </div>
    </details>
  );
}

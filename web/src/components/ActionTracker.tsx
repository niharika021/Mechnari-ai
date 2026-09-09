"use client";

import { useState } from "react";
import type { SheetResult, SheetRow } from "@/lib/api";
import { ApBadge, Button, Callout, Card, MetricTile } from "@/components/ui";

/**
 * Working the actions on a generated report.
 *
 * This is where a DFMEA stops being paperwork. The analysis is already
 * drafted; what remains is the part that actually prevents failures -
 * somebody owning each recommended action, doing it, and saying when.
 *
 * Marking an action done stamps the completion time from the browser
 * clock and writes it into the report, so by the time Quality opens it
 * the record already shows what was done and when. That changes their
 * question from "is this analysis plausible" to "has the work happened",
 * which is the one worth asking.
 *
 * A completion can be un-marked. Real work gets recorded early and
 * corrected; a stamp that cannot be undone would just push people to
 * leave it blank.
 */
export function ActionTracker({
  result,
  onChange,
  highPriorityFirst = true,
}: {
  result: SheetResult;
  onChange: (next: SheetResult) => void;
  highPriorityFirst?: boolean;
}) {
  const [onlyOpen, setOnlyOpen] = useState(false);

  const allRows = result.items.flatMap((item) => item.rows);
  const withAction = allRows.filter((r) => r.recommended_action?.trim());
  const done = withAction.filter((r) => r.completed_date);
  const openHigh = withAction.filter(
    (r) => !r.completed_date && r.action_priority === "H",
  );
  const unowned = withAction.filter((r) => !r.completed_date && !r.responsibility?.trim());

  function patchRow(itemIndex: number, modeId: string, patch: Partial<SheetRow>) {
    onChange({
      ...result,
      items: result.items.map((item, i) =>
        i !== itemIndex
          ? item
          : {
              ...item,
              rows: item.rows.map((r) =>
                r.mode_id === modeId ? { ...r, ...patch } : r,
              ),
            },
      ),
    });
  }

  return (
    <div className="flex flex-col gap-5">
      <Card className="px-5 py-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h3 className="font-display text-[15px] font-semibold text-ink">
              Actions — {done.length} of {withAction.length} closed
            </h3>
            <p className="mt-1 max-w-[80ch] text-xs leading-relaxed text-ink-faint">
              Assign an owner, record what was actually done, and mark it
              complete. The completion time is written into the report, so
              Quality sees the work rather than only the analysis. Everything
              here stays editable.
            </p>
          </div>
          <Button onClick={() => setOnlyOpen((v) => !v)}>
            {onlyOpen ? "Show all actions" : "Show only open"}
          </Button>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-px overflow-hidden rounded-[10px] border border-border bg-border sm:grid-cols-4">
          <div className="bg-bg">
            <MetricTile label="Actions closed" value={`${done.length}/${withAction.length}`} />
          </div>
          <div className="bg-bg">
            <MetricTile
              label="Open at High priority"
              value={openHigh.length}
              tone={openHigh.length > 0 ? "crit" : "default"}
            />
          </div>
          <div className="bg-bg">
            <MetricTile
              label="Open with no owner"
              value={unowned.length}
              tone={unowned.length > 0 ? "crit" : "default"}
            />
          </div>
          <div className="bg-bg">
            <MetricTile
              label="Completion"
              value={
                withAction.length === 0
                  ? "—"
                  : `${Math.round((done.length / withAction.length) * 100)}%`
              }
              tone="accent"
            />
          </div>
        </div>

        {openHigh.length > 0 ? (
          <div className="mt-3">
            <Callout tone="warn">
              {openHigh.length} High-priority action
              {openHigh.length === 1 ? "" : "s"} still open. Quality can see
              that too — it is not hidden by sending the report.
            </Callout>
          </div>
        ) : null}
      </Card>

      {result.items.map((item, itemIndex) => {
        const rows = item.rows
          .filter((r) => r.recommended_action?.trim())
          .filter((r) => (onlyOpen ? !r.completed_date : true))
          .slice()
          .sort((a, b) => {
            if (!highPriorityFirst) return 0;
            const rank = { H: 0, M: 1, L: 2 } as const;
            // Open before closed, then by priority - the list should read
            // as a to-do, not as a table dump.
            const openA = a.completed_date ? 1 : 0;
            const openB = b.completed_date ? 1 : 0;
            if (openA !== openB) return openA - openB;
            return rank[a.action_priority] - rank[b.action_priority];
          });

        if (rows.length === 0) return null;

        return (
          <Card key={`${item.part_number}-${itemIndex}`} className="px-5 py-4">
            <div className="flex flex-wrap items-baseline gap-x-3">
              <span className="font-mono text-sm font-semibold text-accent">
                {item.part_number || "(no part number)"}
              </span>
              <h4 className="font-display text-[14px] font-semibold text-ink">
                {item.item_interface}
              </h4>
            </div>

            <div className="mt-3 flex flex-col gap-2.5">
              {rows.map((row) => (
                <ActionCard
                  key={row.mode_id}
                  row={row}
                  onPatch={(patch) => patchRow(itemIndex, row.mode_id, patch)}
                />
              ))}
            </div>
          </Card>
        );
      })}
    </div>
  );
}

function ActionCard({
  row,
  onPatch,
}: {
  row: SheetRow;
  onPatch: (patch: Partial<SheetRow>) => void;
}) {
  const closed = Boolean(row.completed_date);

  function markDone() {
    // The browser clock, in ISO with an offset, so the stamp still means
    // something when it is read in another timezone.
    onPatch({ completed_date: new Date().toISOString() });
  }

  return (
    <div
      className={`rounded-[9px] border px-3.5 py-3 ${
        closed ? "border-ok bg-ok-soft/40" : "border-border bg-surface"
      }`}
    >
      <div className="flex flex-wrap items-start gap-3">
        <div className="min-w-[220px] flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <ApBadge ap={row.action_priority} />
            <span className="text-[13px] font-semibold text-ink">
              {row.failure_mode}
            </span>
            {closed ? (
              <span className="rounded-full bg-ok-soft px-2 py-0.5 font-mono text-[9.5px] uppercase tracking-wide text-ok">
                closed
              </span>
            ) : null}
          </div>
          <p className="mt-1.5 text-[12.5px] leading-relaxed text-ink-soft">
            {row.recommended_action}
          </p>
          {row.reassessment_basis ? (
            <p className="mt-1 text-[11px] leading-snug text-accent">
              {row.reassessment_basis}
            </p>
          ) : null}
        </div>

        <div className="shrink-0">
          {closed ? (
            <div className="text-right">
              <div className="font-mono text-[10px] uppercase tracking-wider text-ink-faint">
                Completed
              </div>
              <div className="font-mono text-[11.5px] text-ok">
                {formatStamp(row.completed_date)}
              </div>
              <button
                type="button"
                onClick={() => onPatch({ completed_date: "" })}
                className="mt-1 text-[11px] font-semibold text-ink-faint hover:text-ink"
              >
                reopen
              </button>
            </div>
          ) : (
            <Button variant="primary" onClick={markDone}>
              ✓ Mark done
            </Button>
          )}
        </div>
      </div>

      <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <Field label="Responsibility">
          <input
            value={row.responsibility}
            onChange={(e) => onPatch({ responsibility: e.target.value })}
            placeholder="Who owns this"
            className="w-full rounded-[7px] border border-border-strong bg-bg-elevated px-2.5 py-1.5 text-[12.5px] text-ink placeholder:text-ink-faint focus:border-accent focus:outline-none"
          />
        </Field>
        <Field label="Target completion date">
          <input
            type="date"
            value={row.target_completion_date?.slice(0, 10) ?? ""}
            onChange={(e) => onPatch({ target_completion_date: e.target.value })}
            className="w-full rounded-[7px] border border-border-strong bg-bg-elevated px-2.5 py-1.5 text-[12.5px] text-ink focus:border-accent focus:outline-none"
          />
        </Field>
        <Field label="Test reference">
          <input
            value={row.test_reference}
            onChange={(e) => onPatch({ test_reference: e.target.value })}
            placeholder="Test plan / report number"
            className="w-full rounded-[7px] border border-border-strong bg-bg-elevated px-2.5 py-1.5 text-[12.5px] text-ink placeholder:text-ink-faint focus:border-accent focus:outline-none"
          />
        </Field>
        <div className="sm:col-span-2 lg:col-span-3">
          <Field label="Action taken">
            <textarea
              value={row.action_taken}
              onChange={(e) => onPatch({ action_taken: e.target.value })}
              rows={2}
              placeholder="What was actually done - the change made, the test run, the specification updated"
              className="w-full resize-y rounded-[7px] border border-border-strong bg-bg-elevated px-2.5 py-1.5 text-[12.5px] leading-relaxed text-ink placeholder:text-ink-faint focus:border-accent focus:outline-none"
            />
          </Field>
        </div>
      </div>

      {closed && !row.action_taken?.trim() ? (
        <p className="mt-2 text-[11.5px] text-warn">
          Marked done with nothing recorded in &ldquo;action taken&rdquo;. Quality
          will see the date but not what changed.
        </p>
      ) : null}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="mb-1 font-mono text-[10px] uppercase tracking-wider text-ink-faint">
        {label}
      </div>
      {children}
    </div>
  );
}

function formatStamp(iso: string): string {
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString(undefined, {
      year: "numeric",
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

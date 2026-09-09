"use client";

import { Button, Callout, Card, StatusPill } from "@/components/ui";
import type { AnyReportSummary } from "@/lib/reportStore";

/**
 * The engineer's own generated reports.
 *
 * A DFMEA for a 10-14 part package is a week of work, so the assumption
 * that it happens in one browser session was wrong. These persist between
 * visits, which is the difference between a tool an engineer can actually
 * use for the real job and a demo.
 */
export function MyReports({
  reports,
  storageOk,
  onOpen,
  onDelete,
}: {
  reports: AnyReportSummary[];
  storageOk: boolean;
  onOpen: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  if (!storageOk) {
    return (
      <Callout tone="warn">
        This browser is blocking local storage, so generated reports cannot be
        kept between visits. Everything still works — it just will not be here
        after a reload.
      </Callout>
    );
  }

  if (reports.length === 0) return null;

  return (
    <Card className="px-5 py-4">
      <h3 className="font-display text-[15px] font-semibold text-ink">
        My reports — {reports.length}
      </h3>
      <p className="mt-1 max-w-[80ch] text-xs leading-relaxed text-ink-faint">
        Reopen one to keep working its actions. Sending to Quality does not
        remove it — you keep your copy. Reports marked{" "}
        <span className="font-mono text-[10px] uppercase text-ink-faint">
          this browser
        </span>{" "}
        were made signed out and stay on this machine; signing in keeps new
        ones with your account instead.
      </p>

      <div className="mt-3 overflow-hidden rounded-[8px] border border-border">
        <table className="w-full text-left text-[13px]">
          <thead>
            <tr className="border-b border-border bg-bg-elevated font-mono text-[10px] uppercase tracking-wide text-ink-faint">
              <th className="px-3 py-2">Report</th>
              <th className="px-3 py-2">Rows</th>
              <th className="px-3 py-2">Updated</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {reports.map((r) => (
              <tr key={r.id} className="border-b border-border last:border-none">
                <td className="px-3 py-2">
                  <span className="font-semibold text-ink">{r.title}</span>
                  <span className="ml-2 font-mono text-[10px] text-ink-faint">
                    {r.id}
                  </span>
                  <span className="mt-0.5 block text-[11px] text-ink-faint">
                    {r.systemPackage}
                    {r.partCount > 1 ? ` · ${r.partCount} parts` : ""}
                    {!r.remote ? (
                      <span className="ml-1.5 rounded-full bg-surface-hover px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wide">
                        this browser
                      </span>
                    ) : null}
                  </span>
                </td>
                <td className="px-3 py-2 font-mono">{r.rowCount}</td>
                <td className="px-3 py-2 font-mono text-[11.5px] text-ink-soft">
                  {new Date(r.updatedAt).toLocaleString(undefined, {
                    month: "short",
                    day: "2-digit",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </td>
                <td className="px-3 py-2">
                  {r.submittedAt ? (
                    <span className="inline-flex flex-col gap-0.5">
                      <StatusPill status="approved" />
                      <span className="font-mono text-[9.5px] text-ink-faint">
                        {r.draftIds.join(", ")}
                      </span>
                    </span>
                  ) : (
                    <StatusPill status="needs_review" />
                  )}
                </td>
                <td className="px-3 py-2">
                  <div className="flex justify-end gap-2">
                    <Button onClick={() => onOpen(r.id)}>Open</Button>
                    <button
                      type="button"
                      onClick={() => onDelete(r.id)}
                      className="text-xs font-semibold text-ink-faint hover:text-crit"
                    >
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

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
      <h2 className="font-display text-lg font-semibold text-ink">
        My reports — {reports.length}
      </h2>
      {/* One line, not five. The two caveats that used to be spelled out
          here - that sending to Quality leaves you your copy, and what
          the "this browser" tag means - are both already answered at the
          point they matter: the tag itself, and the submit button. Copy
          that restates what the interface shows is copy nobody reads. */}
      <p className="mt-0.5 text-sm text-ink-faint">
        Reopen one to keep working its actions.
      </p>

      <div className="mt-3 overflow-hidden rounded-md border border-border">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-border bg-sunken font-mono text-micro uppercase text-ink-faint">
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
                  <span className="ml-2 font-mono text-micro text-ink-faint">
                    {r.id}
                  </span>
                  <span className="mt-0.5 block text-micro text-ink-faint">
                    {r.systemPackage}
                    {r.partCount > 1 ? ` · ${r.partCount} parts` : ""}
                    {!r.remote ? (
                      <span className="ml-1.5 rounded-full bg-sunken px-1.5 py-0.5 font-mono text-micro uppercase">
                        this browser
                      </span>
                    ) : null}
                  </span>
                </td>
                <td className="px-3 py-2 font-mono">{r.rowCount}</td>
                <td className="px-3 py-2 font-mono text-label text-ink-soft">
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
                      <span className="font-mono text-micro text-ink-faint">
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
                      className="text-label font-semibold text-ink-faint hover:text-crit"
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

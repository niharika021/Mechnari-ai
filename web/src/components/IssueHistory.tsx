"use client";

import { useMemo, useState } from "react";
import { api, type IssueRecord, type IssueSummaryRow } from "@/lib/api";
import { Card, Spinner } from "@/components/ui";

export function IssueHistory({ summary }: { summary: IssueSummaryRow[] }) {
  const [query, setQuery] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [detail, setDetail] = useState<Record<string, IssueRecord[]>>({});
  const [loading, setLoading] = useState<string | null>(null);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return summary;
    return summary.filter(
      (row) =>
        row.part_id.toLowerCase().includes(q) ||
        row.item_reference.toLowerCase().includes(q),
    );
  }, [summary, query]);

  async function toggle(partId: string) {
    if (expanded === partId) {
      setExpanded(null);
      return;
    }
    setExpanded(partId);
    if (!detail[partId]) {
      setLoading(partId);
      try {
        const rows = await api.issuesForPart(partId);
        setDetail((prev) => ({ ...prev, [partId]: rows }));
      } finally {
        setLoading(null);
      }
    }
  }

  const totalIssues = summary.reduce((sum, r) => sum + r.issue_count, 0);
  const totalClaims = summary.reduce((sum, r) => sum + r.total_claims, 0);

  return (
    <Card className="px-5 py-4">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h3 className="font-display text-lg font-semibold text-ink">
            Warranty &amp; field issue history
          </h3>
          <p className="mt-0.5 max-w-[70ch] text-sm text-ink-faint">
            Every 8D on record, against every part that has ever had one - active
            on the BOM today or retired. {summary.length} parts, {totalIssues}{" "}
            issues, {totalClaims.toLocaleString()} claims behind them. Search by
            part ID or name; open a row for the individual reports.
          </p>
        </div>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search part ID or name…"
          className="w-full max-w-[240px] rounded-md border border-border-strong bg-panel px-3 py-2 text-body text-ink placeholder:text-ink-faint focus:border-accent"
        />
      </div>

      <div className="mt-3.5 overflow-x-auto rounded-md border border-border">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-border bg-sunken font-mono text-micro uppercase text-ink-faint">
              <th className="px-3 py-2">Part</th>
              <th className="px-3 py-2">Issues</th>
              <th className="px-3 py-2">Claims</th>
              <th className="px-3 py-2">Latest report</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-3 py-4 text-center text-ink-faint">
                  No part matches &ldquo;{query}&rdquo;.
                </td>
              </tr>
            ) : (
              filtered.map((row) => (
                <PartRow
                  key={row.part_id}
                  row={row}
                  open={expanded === row.part_id}
                  onToggle={() => toggle(row.part_id)}
                  loading={loading === row.part_id}
                  issues={detail[row.part_id]}
                />
              ))
            )}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function PartRow({
  row,
  open,
  onToggle,
  loading,
  issues,
}: {
  row: IssueSummaryRow;
  open: boolean;
  onToggle: () => void;
  loading: boolean;
  issues?: IssueRecord[];
}) {
  return (
    <>
      <tr
        onClick={onToggle}
        className="cursor-pointer border-b border-border last:border-none hover:bg-surface-hover"
      >
        <td className="px-3 py-2">
          <span className="mr-1.5 inline-block w-3 text-ink-faint">{open ? "▾" : "▸"}</span>
          <span className="font-semibold text-ink">{row.item_reference}</span>
          <span className="ml-1.5 font-mono text-micro text-ink-faint">{row.part_id}</span>
        </td>
        <td className="px-3 py-2 font-mono">{row.issue_count}</td>
        <td className="px-3 py-2 font-mono">{row.total_claims}</td>
        <td className="px-3 py-2 font-mono text-ink-soft">
          {row.latest_report?.slice(0, 10)}
        </td>
      </tr>
      {open ? (
        <tr className="border-b border-border bg-bg last:border-none">
          <td colSpan={4} className="px-3 py-3">
            {loading ? (
              <Spinner />
            ) : (
              <div className="flex flex-col gap-2">
                {(issues ?? []).map((issue) => (
                  <div
                    key={issue.issue_id}
                    className="rounded-md border border-border bg-panel px-3 py-2.5 text-sm"
                  >
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                      <span className="font-mono text-label font-semibold text-accent">
                        {issue.issue_id}
                      </span>
                      <span className="text-ink-faint">
                        {issue.report_date?.slice(0, 10)}
                      </span>
                      <span className="font-semibold text-ink">
                        {issue.failure_mode ?? issue.mode_id}
                      </span>
                      <span className="ml-auto font-mono text-ink-soft">
                        {issue.claim_count} claims · S{issue.observed_severity}
                      </span>
                    </div>
                    <p className="mt-1.5 leading-relaxed text-ink-soft">
                      {issue.description}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </td>
        </tr>
      ) : null}
    </>
  );
}

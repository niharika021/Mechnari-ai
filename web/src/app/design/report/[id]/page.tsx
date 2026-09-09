"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import type { SheetResult, SheetRow } from "@/lib/api";
import { Button, Callout, Card } from "@/components/ui";
import { DfmeaSheet } from "@/components/DfmeaSheet";
import {
  loadReport,
  persistResult,
  persistSubmission,
  type StoredReport,
} from "@/lib/reportStore";
import { useAuth } from "@/lib/auth";

/**
 * One report, on its own URL.
 *
 * A DFMEA is a document, so it gets an address rather than being a
 * transient state of the intake form. That makes it bookmarkable, the
 * back button behave, and reopening it from the list mean the same thing
 * as arriving at it directly.
 *
 * A client component on purpose: the report lives in this browser's
 * storage, so there is nothing for a server to render.
 */
export default function ReportPage() {
  const params = useParams<{ id: string }>();
  const id = params?.id ?? "";

  const { user, loading: authLoading } = useAuth();
  const [report, setReport] = useState<StoredReport | null>(null);
  const [remote, setRemote] = useState(false);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    // Wait for auth to settle: asking the server for a report before the
    // token exists would 404 a report the engineer does own.
    if (authLoading) return;
    let cancelled = false;
    loadReport(id, Boolean(user)).then((found) => {
      if (cancelled) return;
      setReport(found?.report ?? null);
      setRemote(Boolean(found?.remote));
      setLoaded(true);
    });
    return () => {
      cancelled = true;
    };
  }, [id, user, authLoading]);

  /**
   * Edits are written straight through - there is no save button, because
   * a save button is a way to lose work.
   */
  function patchRow(itemIndex: number, modeId: string, patch: Partial<SheetRow>) {
    setReport((prev) => {
      if (!prev) return prev;
      const next: SheetResult = {
        ...prev.result,
        items: prev.result.items.map((item, i) =>
          i !== itemIndex
            ? item
            : {
                ...item,
                rows: item.rows.map((r) =>
                  r.mode_id === modeId ? { ...r, ...patch } : r,
                ),
              },
        ),
      };
      void persistResult(prev.id, remote, next);
      return { ...prev, result: next };
    });
  }

  if (!loaded || authLoading) {
    return <p className="text-[13px] text-ink-faint">Loading…</p>;
  }

  if (!report) {
    return (
      <div className="flex flex-col gap-4">
        <Callout tone="warn">
          No report with id <span className="font-mono">{id}</span> in this
          browser.
          {user
            ? " It may have been deleted, or it belongs to another account."
            : " Reports made while signed in follow your account - sign in to see them here."}
        </Callout>
        <Link href="/design">
          <Button>← Back to part intake</Button>
        </Link>
      </div>
    );
  }

  const rows = report.result.items.flatMap((i) => i.rows);
  const actionable = rows.filter((r) => r.recommended_action?.trim());
  const closed = actionable.filter((r) => r.completed_date).length;

  return (
    <div className="flex flex-col gap-5">
      <Card className="px-5 py-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="font-mono text-[10.5px] uppercase tracking-wider text-ink-faint">
              DFMEA report {report.id}
            </div>
            <h2 className="mt-0.5 font-display text-lg font-bold text-ink">
              {report.title}
            </h2>
            <p className="mt-1 text-xs text-ink-faint">
              {report.systemPackage} · generated{" "}
              {new Date(report.createdAt).toLocaleString(undefined, {
                month: "short",
                day: "2-digit",
                year: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              })}
              {report.submittedAt ? (
                <>
                  {" · "}
                  <span className="text-ok">
                    sent to Quality as {report.draftIds.join(", ")}
                  </span>
                </>
              ) : null}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-3">
            <div className="text-right">
              <div className="font-mono text-[10px] uppercase tracking-wider text-ink-faint">
                Actions closed
              </div>
              <div
                className={`font-mono text-lg font-bold ${
                  actionable.length > 0 && closed === actionable.length
                    ? "text-ok"
                    : "text-ink"
                }`}
              >
                {closed}/{actionable.length}
              </div>
            </div>
            <Link href="/design">
              <Button>← Part intake</Button>
            </Link>
          </div>
        </div>
      </Card>

      <DfmeaSheet
        result={report.result}
        approved
        systemPackage={report.systemPackage}
        onRowChange={patchRow}
        onSubmitted={(draftIds) => {
          void persistSubmission(report.id, remote, draftIds);
          setReport((prev) =>
            prev
              ? { ...prev, submittedAt: new Date().toISOString(), draftIds }
              : prev,
          );
        }}
      />
    </div>
  );
}

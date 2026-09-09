"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api, type Draft } from "@/lib/api";
import { Button, Callout, Card, Spinner, StatusPill, TextArea } from "@/components/ui";

/** Where a row came from. A blank source means the draft predates the
 *  review step - not that nobody checked it. */
function RowSource({ provenance }: { provenance?: string }) {
  if (!provenance) return <span className="text-[11px] text-ink-faint">-</span>;
  const label =
    provenance === "engineer_added"
      ? "Engineer's own"
      : provenance === "edited"
        ? "Edited"
        : "Accepted";
  const tone =
    provenance === "engineer_added"
      ? "bg-accent-soft text-accent-strong"
      : provenance === "edited"
        ? "bg-warn-soft text-warn"
        : "bg-ok-soft text-ok";
  return (
    <span
      className={`inline-block whitespace-nowrap rounded-full px-2 py-0.5 font-mono text-[9.5px] uppercase tracking-wide ${tone}`}
    >
      {label}
    </span>
  );
}

export function QueueBrowser({
  initialQueue,
  selectedDraftId,
}: {
  initialQueue: Draft[];
  selectedDraftId?: string;
}) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [queue, setQueue] = useState(initialQueue);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [loadingDraft, setLoadingDraft] = useState(false);
  const [comments, setComments] = useState("");

  const activeId = searchParams.get("draft") ?? selectedDraftId;

  useEffect(() => {
    if (!activeId) {
      setDraft(null);
      return;
    }
    setLoadingDraft(true);
    api
      .draft(activeId)
      .then((d) => {
        setDraft(d);
        setComments(d.review_comments ?? "");
      })
      .catch(() => setDraft(null))
      .finally(() => setLoadingDraft(false));
  }, [activeId]);

  function select(id: string) {
    router.push(`/quality?draft=${encodeURIComponent(id)}`, { scroll: false });
  }

  async function refreshQueue() {
    const fresh = await api.queue();
    setQueue(fresh);
  }

  async function act(status: Draft["status"]) {
    if (!draft) return;
    await api.setDraftStatus(draft.draft_id, status, comments);
    const updated = await api.draft(draft.draft_id);
    setDraft(updated);
    await refreshQueue();
  }

  return (
    <div className="grid gap-5 lg:grid-cols-[300px_1fr]">
      <Card className="max-h-[520px] overflow-y-auto">
        {queue.length === 0 ? (
          <p className="p-4 text-[13px] text-ink-faint">
            No drafts submitted yet - use the Design Engineer tab to send one.
          </p>
        ) : (
          <ul>
            {queue.map((d) => (
              <li key={d.draft_id} className="border-b border-border last:border-none">
                <button
                  type="button"
                  onClick={() => select(d.draft_id)}
                  className={`flex w-full flex-col gap-1.5 px-4 py-3 text-left transition-colors ${
                    d.draft_id === activeId ? "bg-accent-soft" : "hover:bg-surface-hover"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-xs font-semibold text-ink">
                      {d.draft_id}
                    </span>
                    <StatusPill status={d.status} />
                  </div>
                  <span className="text-sm text-ink">{d.part_name}</span>
                  <span className="text-xs text-ink-faint">
                    Submitted by {d.submitted_by} · {d.accepted_rows.length} rows
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card className="px-5 py-4">
        {!activeId ? (
          <p className="text-[13px] text-ink-faint">
            Select a submitted draft on the left, or audit an existing part below.
          </p>
        ) : loadingDraft ? (
          <Spinner />
        ) : !draft ? (
          <p className="text-[13px] text-ink-faint">That draft could not be found.</p>
        ) : (
          <div className="flex flex-col gap-4">
            <div>
              <h4 className="font-display text-[15px] font-semibold text-ink">
                {draft.draft_id} — {draft.part_name}
              </h4>
              <p className="text-xs text-ink-faint">
                {draft.part_type_name} · submitted by {draft.submitted_by} ·{" "}
                {draft.submitted_at.slice(0, 19).replace("T", " ")}
              </p>
            </div>

            {draft.declined_rows.some((r) => r.action_priority === "H") ? (
              <Callout tone="warn">
                <strong className="block pb-1">
                  {draft.declined_rows.filter((r) => r.action_priority === "H").length}{" "}
                  High-priority candidate(s) were declined by the design engineer:
                </strong>
                <ul className="flex flex-col gap-0.5">
                  {draft.declined_rows
                    .filter((r) => r.action_priority === "H")
                    .map((r) => (
                      <li key={r.mode_id}>
                        {r.failure_mode} (S={r.severity}) — learned from {r.learned_from}
                      </li>
                    ))}
                </ul>
              </Callout>
            ) : (
              <Callout tone="ok">No High-priority candidates were declined.</Callout>
            )}

            <div>
              <h5 className="mb-2 text-sm font-semibold text-ink">
                Accepted rows ({draft.accepted_rows.length})
              </h5>
              <div className="overflow-x-auto rounded-[8px] border border-border">
                <table className="w-full text-left text-[13px]">
                  <thead>
                    <tr className="border-b border-border bg-bg-elevated font-mono text-[10.5px] uppercase tracking-wide text-ink-faint">
                      <th className="px-3 py-2">Failure Mode</th>
                      <th className="px-3 py-2">S</th>
                      <th className="px-3 py-2">O</th>
                      <th className="px-3 py-2">D</th>
                      <th className="px-3 py-2">AP</th>
                      <th className="px-3 py-2">Action closed</th>
                      <th className="px-3 py-2">Source</th>
                    </tr>
                  </thead>
                  <tbody>
                    {draft.accepted_rows.map((r) => (
                      <tr key={r.mode_id} className="border-b border-border align-top last:border-none">
                        <td className="px-3 py-2">
                          {r.failure_mode}
                          {/* The reasons the engineer gave, carried through the
                              handoff precisely so a reviewer sees them. */}
                          {r.occurrence_override_reason ? (
                            <span className="mt-1 block text-[11px] leading-snug text-warn">
                              Occ override: {r.occurrence_override_reason}
                            </span>
                          ) : null}
                          {r.severity_dispute_note ? (
                            <span className="mt-1 block text-[11px] leading-snug text-warn">
                              Sev disputed: {r.severity_dispute_note}
                            </span>
                          ) : null}
                        </td>
                        <td className="px-3 py-2 font-mono">{r.severity}</td>
                        <td className="px-3 py-2 font-mono">{r.occurrence}</td>
                        <td className="px-3 py-2 font-mono">{r.detection}</td>
                        <td className="px-3 py-2 font-mono">{r.action_priority}</td>
                        {/* Whether the engineer actually did the work, and
                            when. This is what changes Quality's question from
                            "is the analysis plausible" to "has it happened". */}
                        <td className="px-3 py-2">
                          {r.completed_date ? (
                            <span className="block font-mono text-[11px] text-ok">
                              {new Date(r.completed_date).toLocaleString(undefined, {
                                month: "short",
                                day: "2-digit",
                                hour: "2-digit",
                                minute: "2-digit",
                              })}
                              {r.action_taken ? (
                                <span className="mt-0.5 block font-sans text-[11px] leading-snug text-ink-soft">
                                  {r.action_taken}
                                </span>
                              ) : (
                                <span className="mt-0.5 block font-sans text-[11px] text-warn">
                                  no record of what changed
                                </span>
                              )}
                            </span>
                          ) : (
                            <span className="text-[11px] text-ink-faint">open</span>
                          )}
                        </td>
                        <td className="px-3 py-2">
                          <RowSource provenance={r.provenance} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <TextArea
              value={comments}
              onChange={(e) => setComments(e.target.value)}
              placeholder="Comments back to the design engineer…"
              rows={2}
            />
            <div className="flex gap-2.5">
              <Button variant="secondary" onClick={() => act("returned")} className="flex-1">
                ↩️ Return with Comments
              </Button>
              <Button variant="primary" onClick={() => act("approved")} className="flex-1">
                ✅ Approve
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}

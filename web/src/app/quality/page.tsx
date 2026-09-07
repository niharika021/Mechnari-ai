import { api } from "@/lib/api";
import { QueueBrowser } from "./QueueBrowser";
import { PartAuditor } from "./PartAuditor";

export default async function QualityEngineerPage({
  searchParams,
}: {
  searchParams: Promise<{ draft?: string }>;
}) {
  const { draft } = await searchParams;
  const [queue, parts] = await Promise.all([api.queue(), api.parts()]);

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h2 className="font-display text-lg font-bold text-ink">Review Queue</h2>
        <p className="mt-1 max-w-[80ch] text-[13px] text-ink-faint">
          Audits, not drafting. Submitted drafts and existing parts on file,
          checked against the organization&apos;s failure-effect registry and the
          warranty record before sign-off - the same deterministic engines, read
          as an audit trail. Selecting a draft updates the URL, so a review can
          be linked directly.
        </p>
      </div>

      <QueueBrowser initialQueue={queue} selectedDraftId={draft} />

      <div className="border-t border-border pt-6">
        <h3 className="font-display text-[15px] font-semibold text-ink">
          Audit an existing part
        </h3>
        <p className="mt-1 text-xs text-ink-faint">
          The same audit suite, run against a part already on file: severity
          consistency, occurrence vs. the warranty record, and coverage.
        </p>
        <PartAuditor parts={parts} />
      </div>
    </div>
  );
}

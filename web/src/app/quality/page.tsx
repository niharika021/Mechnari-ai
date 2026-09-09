import { api } from "@/lib/api";
import { PageHeader } from "@/components/RoleNav";
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
      <PageHeader
        title="Review Queue"
        purpose="Audit submitted drafts against the registry and the warranty record."
      />

      <QueueBrowser initialQueue={queue} selectedDraftId={draft} />

      <section className="border-t border-border pt-6">
        <h2 className="font-display text-lg font-semibold text-ink">
          Audit an existing part
        </h2>
        <p className="mt-0.5 text-sm text-ink-faint">
          Severity consistency, Occurrence against the warranty record, and
          coverage — for a part already on file.
        </p>
        <PartAuditor parts={parts} />
      </section>
    </div>
  );
}

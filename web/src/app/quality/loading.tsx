import { PageHeader } from "@/components/RoleNav";
import { Card, Skeleton } from "@/components/ui";

/**
 * The Quality view has the same problem as the program rollup, one
 * endpoint fewer: it waits on the review queue and the part list before
 * anything renders. Same treatment - the real header immediately, the
 * queue as skeleton rows on the layout they will occupy.
 */
export default function Loading() {
  return (
    <div className="flex flex-col gap-8" aria-busy="true">
      <PageHeader
        title="Review Queue"
        purpose="Audit submitted drafts against the registry and the warranty record."
      />

      <span className="sr-only" role="status">
        Loading the review queue…
      </span>

      {/* Must match QueueBrowser's own grid exactly, or the columns jump
          width the moment the real data replaces this. */}
      <div className="grid gap-5 lg:grid-cols-[300px_1fr]">
        <div className="flex flex-col gap-2.5">
          {[0, 1, 2, 3, 4].map((i) => (
            <Card key={i} className="px-4 py-3">
              <div className="flex items-center justify-between gap-3">
                <Skeleton className="h-2.5 w-20" />
                <Skeleton className="h-4 w-24 rounded-full" />
              </div>
              <Skeleton className="mt-2.5 h-3 w-40" />
              <Skeleton className="mt-2 h-2.5 w-32" />
            </Card>
          ))}
        </div>
        <Card className="px-5 py-4">
          <Skeleton className="h-3 w-64" />
        </Card>
      </div>
    </div>
  );
}

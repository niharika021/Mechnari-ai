import { PageHeader } from "@/components/RoleNav";
import { Card, Skeleton } from "@/components/ui";

/**
 * The design view fetches part types, system packages and the part list
 * before the intake form can render its dropdowns, so it has the same
 * blank-tab pause as the other two. The skeleton mirrors the form's
 * two-column field grid, which is what appears.
 */
export default function Loading() {
  return (
    <div aria-busy="true">
      <PageHeader
        title="Part Intake"
        purpose="Draft a DFMEA, or open one already on file."
      />

      <span className="sr-only" role="status">
        Loading part types…
      </span>

      <div className="mt-5 flex flex-col gap-6">
        <Card className="px-5 pb-4 pt-4">
          <div className="mb-4 flex flex-wrap items-center gap-2">
            <Skeleton className="h-8 w-24 rounded-md" />
            <Skeleton className="h-8 w-36 rounded-md" />
            <Skeleton className="h-8 w-40 rounded-md" />
          </div>
          <Skeleton className="h-2.5 w-44" />
          <Skeleton className="mt-1.5 h-9 w-full rounded-md" />
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            {[0, 1].map((i) => (
              <div key={i}>
                <Skeleton className="h-2.5 w-24" />
                <Skeleton className="mt-1.5 h-9 w-full rounded-md" />
              </div>
            ))}
          </div>
          <div className="mt-4">
            <Skeleton className="h-2.5 w-32" />
            <Skeleton className="mt-1.5 h-[58px] w-full rounded-md" />
          </div>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            {[0, 1].map((i) => (
              <div key={i}>
                <Skeleton className="h-2.5 w-28" />
                <Skeleton className="mt-1.5 h-9 w-full rounded-md" />
              </div>
            ))}
          </div>
          <Skeleton className="mt-4 h-9 w-36 rounded-md" />
        </Card>
      </div>
    </div>
  );
}

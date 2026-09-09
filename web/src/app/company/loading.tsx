import { PageHeader } from "@/components/RoleNav";
import { Card, Skeleton } from "@/components/ui";

/**
 * Shown while the page's server component is fetching.
 *
 * Next.js renders this instantly on navigation and swaps in the real
 * page when it resolves, so the tab responds to the click immediately
 * instead of appearing to hang. This view waits on five endpoints in
 * parallel - gap metrics, the backtest, its cutoff sweep, the gap list
 * and the issue summary - and the slowest measured ~1.6s against the
 * deployed API, which was the couple of seconds of nothing.
 *
 * The header is the real one, not a placeholder: the title and purpose
 * are static, so showing them immediately means the page identifies
 * itself while the numbers are still coming. Only the figures are
 * skeletons, and they are laid out on the same grid as the real tiles
 * so nothing jumps when they arrive.
 */
export default function Loading() {
  return (
    <div className="flex flex-col gap-6" aria-busy="true">
      <PageHeader
        title="Risk Coverage"
        purpose="Coverage across the program, open safety gaps, and the backtest behind them."
      />

      <span className="sr-only" role="status">
        Loading program figures…
      </span>

      {/* Same 5-up grid and hairline dividers as the real tiles. */}
      <div className="grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-border bg-border sm:grid-cols-3 lg:grid-cols-5">
        {/*
          Bar heights are the real line boxes rather than eyeballed - micro
          at 11px/1.45 ≈ 16px for the label, display at 27px/1.18 ≈ 32px
          for the figure - with the tile's own mt-0.5 / mt-1 spacing. Sized
          by eye first and the grid grew 39px when data landed, which is
          the jump a skeleton exists to prevent.

          Only the fourth tile gets a third bar, because only one real tile
          carries a hint (the backtest lift's "72% -> 98% recall"). Giving
          all five a hint made the skeleton uniformly taller than four of
          the tiles it stands in for.

          This is close, not exact. Measured real tiles run 76px without a
          hint to 132px for the one whose hint wraps at narrow widths, so
          the final height depends on text this cannot know. The point is
          to hold roughly the right space, not to promise zero movement.
        */}
        {[0, 1, 2, 3, 4].map((i) => (
          <div key={i} className="bg-panel px-4 pb-3.5 pt-3">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="mt-0.5 h-8 w-16" />
            {i === 3 ? <Skeleton className="mt-1 h-[18px] w-24" /> : null}
          </div>
        ))}
      </div>

      <div className="grid gap-5 lg:grid-cols-[1.3fr_1fr]">
        <Card className="px-5 py-4">
          <Skeleton className="h-4 w-72" />
          <Skeleton className="mt-4 h-[180px] w-full" />
          <Skeleton className="mt-3 h-2.5 w-full" />
          <Skeleton className="mt-1.5 h-2.5 w-4/5" />
        </Card>
        <Card className="px-5 py-4">
          <Skeleton className="h-4 w-56" />
          <div className="mt-4 flex flex-col gap-3">
            {[0, 1, 2, 3, 4].map((i) => (
              <div key={i} className="grid grid-cols-[1fr_auto] items-center gap-3">
                <div className="flex flex-col gap-1.5">
                  <Skeleton className="h-2.5 w-32" />
                  <Skeleton className="h-2 w-full" />
                </div>
                <Skeleton className="h-2.5 w-5" />
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card className="px-5 py-4">
        <Skeleton className="h-4 w-64" />
        <Skeleton className="mt-4 h-[220px] w-full" />
      </Card>
    </div>
  );
}

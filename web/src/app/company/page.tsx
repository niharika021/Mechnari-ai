import { api } from "@/lib/api";
import { PageHeader } from "@/components/RoleNav";
import { Card, MetricTile } from "@/components/ui";
import { BacktestChart } from "@/components/BacktestChart";
import { IssueHistory } from "@/components/IssueHistory";

export default async function CompanyPage() {
  const [gapMetrics, backtest, sweep, gaps, issueSummary] = await Promise.all([
    api.gapMetrics(),
    api.backtest(),
    api.backtestSweep(),
    api.gaps(),
    api.issueSummary(),
  ]);

  const { summary } = backtest;
  const liftPts = Math.round((summary.mechnari_recall - summary.dfmea_recall) * 100);

  const byPackage = new Map<string, number>();
  for (const g of gaps) {
    if (g.standard_severity >= 9) {
      byPackage.set(g.system_package, (byPackage.get(g.system_package) ?? 0) + 1);
    }
  }
  const packageRows = [...byPackage.entries()].sort((a, b) => b[1] - a[1]);
  const maxCount = Math.max(1, ...packageRows.map(([, n]) => n));

  return (
    <div className="flex flex-col gap-6">
      {/*
        "Program Health" was doing no work. Health of what, measured how?
        It could sit on any dashboard in any product. This page answers
        one specific question - how much of the program has been analysed,
        and what risk is still open - so the title says that.

        "Risk Coverage" rather than "Program Risk Coverage" because the
        nav tab already says Program; repeating it in the heading is the
        kind of redundancy that reads as filler.
      */}
      <PageHeader
        title="Risk Coverage"
        purpose="Coverage across the program, open safety gaps, and the backtest behind them."
      />

      <div className="grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-border bg-border sm:grid-cols-3 lg:grid-cols-5">
        {[
          <MetricTile
            key="1"
            label="Parts Covered"
            value={`${gapMetrics.parts_analysed}/${gapMetrics.parts_analysed}`}
          />,
          <MetricTile
            key="2"
            label="Mean DFMEA Coverage"
            value={`${Math.round(gapMetrics.mean_coverage_pct)}%`}
          />,
          <MetricTile
            key="3"
            label="Open Safety Gaps (S≥9)"
            value={gapMetrics.safety_gaps}
            tone="crit"
          />,
          <MetricTile
            key="4"
            label="Backtest Lift vs. Manual"
            value={`+${liftPts} pts`}
            hint={`${Math.round(summary.dfmea_recall * 100)}% → ${Math.round(summary.mechnari_recall * 100)}% recall`}
            tone="accent"
          />,
          <MetricTile
            key="5"
            label="Claims Behind Newly-Caught"
            value={summary.newly_caught_claims}
          />,
        ].map((tile) => (
          <div key={tile.key} className="bg-bg">
            {tile}
          </div>
        ))}
      </div>

      <div className="grid gap-5 lg:grid-cols-[1.3fr_1fr]">
        <Card className="px-5 py-4">
          <h3 className="font-display text-lg font-semibold text-ink">
            Would this have caught what manual review missed?
          </h3>
          <div className="mt-3">
            <BacktestChart sweep={sweep} />
          </div>
          <p className="mt-2 text-xs leading-relaxed text-ink-faint">
            A DFMEA for one 10-14 part assembly runs about a week as a
            cross-functional workshop; a tractor is 1,000+ parts - on the
            order of 70-100 such workshops per program, run by different
            people at different times. That is the actual mechanism behind
            the gap above.
          </p>
        </Card>

        <Card className="px-5 py-4">
          <h3 className="font-display text-lg font-semibold text-ink">
            Open safety gaps by system package
          </h3>
          <div className="mt-3 flex flex-col gap-2.5">
            {packageRows.length === 0 ? (
              <p className="text-sm text-ink-faint">No safety-severity gaps open.</p>
            ) : (
              packageRows.map(([pkg, count]) => (
                <div key={pkg} className="grid grid-cols-[1fr_auto] items-center gap-3">
                  <div className="flex flex-col gap-1">
                    <span className="text-xs text-ink-soft">{pkg}</span>
                    <div className="h-2 rounded-full bg-surface-hover">
                      <div
                        className="h-2 rounded-full bg-crit"
                        style={{ width: `${(count / maxCount) * 100}%` }}
                      />
                    </div>
                  </div>
                  <span className="font-mono text-sm text-ink">{count}</span>
                </div>
              ))
            )}
          </div>
        </Card>
      </div>

      <IssueHistory summary={issueSummary} />
    </div>
  );
}

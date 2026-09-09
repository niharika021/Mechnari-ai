import type { BacktestSummary } from "@/lib/api";

/**
 * Recall of the manual DFMEA vs. Mechnari across knowledge cutoffs.
 * Same drawing as the build dossier and role-view mockup artifacts - one
 * scale, ticks and labels the chart actually reaches, marks and labels
 * kept clear of the drawing's edges.
 */
export function BacktestChart({ sweep }: { sweep: BacktestSummary[] }) {
  const width = 720;
  const height = 300;
  const padLeft = 64;
  const padRight = 96;
  const padTop = 24;
  const padBottom = 44;
  const plotW = width - padLeft - padRight;
  const plotH = height - padTop - padBottom;

  const n = sweep.length;
  const x = (i: number) => padLeft + (n > 1 ? (i / (n - 1)) * plotW : plotW / 2);
  const y = (v: number) => padTop + plotH - v * plotH;

  const dfmeaPoints = sweep.map((s, i) => `${x(i)},${y(s.dfmea_recall)}`).join(" ");
  const mechnariPoints = sweep.map((s, i) => `${x(i)},${y(s.mechnari_recall)}`).join(" ");
  const bandPoints = [
    ...sweep.map((s, i) => `${x(i)},${y(s.dfmea_recall)}`),
    ...sweep
      .slice()
      .reverse()
      .map((s, i) => `${x(n - 1 - i)},${y(s.mechnari_recall)}`),
  ].join(" ");

  const ticks = [0, 0.25, 0.5, 0.75, 1];

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="w-full"
      role="img"
      aria-label="Line chart comparing recall of the manual DFMEA against Mechnari across knowledge cutoffs."
    >
      {ticks.map((t) => (
        <line
          key={t}
          x1={padLeft}
          x2={width - padRight}
          y1={y(t)}
          y2={y(t)}
          stroke="var(--color-border)"
          strokeWidth={1}
        />
      ))}
      {ticks.map((t) => (
        <text
          key={t}
          x={padLeft - 10}
          y={y(t) + 4}
          textAnchor="end"
          fontFamily="var(--font-mono)"
          fontSize={11}
          fill="var(--color-ink-faint)"
        >
          {Math.round(t * 100)}%
        </text>
      ))}

      <polygon points={bandPoints} fill="var(--color-accent-soft)" opacity={0.7} />
      <polyline
        points={dfmeaPoints}
        fill="none"
        stroke="var(--color-ink-soft)"
        strokeWidth={2}
        strokeDasharray="5 4"
      />
      <polyline points={mechnariPoints} fill="none" stroke="var(--color-accent)" strokeWidth={2.5} />

      {sweep.map((s, i) => (
        <circle key={`d${i}`} cx={x(i)} cy={y(s.dfmea_recall)} r={3} fill="var(--color-ink-soft)" />
      ))}
      {sweep.map((s, i) => (
        <circle key={`m${i}`} cx={x(i)} cy={y(s.mechnari_recall)} r={3.5} fill="var(--color-accent)" />
      ))}

      <text
        x={width - padRight + 8}
        y={y(sweep[n - 1]?.mechnari_recall ?? 1) + 4}
        fontFamily="var(--font-mono)"
        fontSize={11}
        fontWeight={600}
        fill="var(--color-accent)"
      >
        Mechnari
      </text>
      <text
        x={width - padRight + 8}
        y={y(sweep[n - 1]?.dfmea_recall ?? 0) + 4}
        fontFamily="var(--font-mono)"
        fontSize={11}
        fontWeight={600}
        fill="var(--color-ink-soft)"
      >
        Manual DFMEA
      </text>

      {sweep.map((s, i) => (
        <text
          key={`x${i}`}
          x={x(i)}
          y={height - padBottom + 20}
          textAnchor="middle"
          fontFamily="var(--font-mono)"
          fontSize={11}
          fill="var(--color-ink-faint)"
        >
          {s.cutoff}
        </text>
      ))}
    </svg>
  );
}

import type { ReactNode } from "react";
import { IconAlert, IconCheck } from "@/components/icons";

/**
 * Shared primitives.
 *
 * The change that matters here is tiering. There used to be one `Card` -
 * one radius, one border, one white fill - wrapped around the hero, the
 * metric tiles, the charts and the panels alike. When every container
 * has identical weight nothing reads as primary, so the eye has no entry
 * point and a page of eight cards is a page of eight equals.
 *
 * Three tiers now, and the rule is that elevation means importance:
 *   panel   - the default. Border only, no shadow.
 *   sunken   - insets: table headers, read-only regions.
 *   raised  - shadowed. Reserved for the form sheet and modals, the two
 *             things that are genuinely "on top of" the page.
 */

export function Card({
  children,
  tier = "panel",
  className = "",
}: {
  children: ReactNode;
  tier?: "panel" | "sunken" | "raised";
  className?: string;
}) {
  const tiers = {
    panel: "border border-border bg-panel",
    sunken: "border border-border bg-sunken",
    raised: "border border-border bg-raised shadow-raised",
  };
  return (
    <div className={`rounded-lg ${tiers[tier]} ${className}`}>{children}</div>
  );
}

export function MetricTile({
  label,
  value,
  hint,
  tone = "default",
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  tone?: "default" | "crit" | "accent";
}) {
  const valueColor =
    tone === "crit" ? "text-crit" : tone === "accent" ? "text-accent" : "text-ink";
  return (
    <div className="bg-panel px-4 pb-3.5 pt-3">
      <div className="font-mono text-micro uppercase text-ink-faint">{label}</div>
      {/* tabular-nums so a column of tiles doesn't jitter between values
          of different digit widths. */}
      <div
        className={`mt-0.5 font-display text-display font-bold tabular-nums ${valueColor}`}
      >
        {value}
      </div>
      {hint ? (
        <div className="mt-1 font-mono text-label tabular-nums text-ink-soft">
          {hint}
        </div>
      ) : null}
    </div>
  );
}

/*
  Action Priority and status are tinted chips - border plus soft fill
  plus coloured text - and never a solid fill. Solid fill is reserved for
  buttons, so "this is a control" and "this is a severity" can never be
  confused at a glance. High additionally gets a heavier border, because
  it is the one value on a DFMEA row that should stop someone.
*/
const AP_STYLES: Record<string, { label: string; className: string }> = {
  H: { label: "High", className: "border-crit bg-crit-soft text-crit font-bold" },
  M: { label: "Medium", className: "border-warn-line bg-warn-soft text-warn" },
  L: { label: "Low", className: "border-ok-line bg-ok-soft text-ok" },
};

const CHIP =
  "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-mono text-micro font-semibold uppercase";

export function ApBadge({ ap }: { ap: string }) {
  const style =
    AP_STYLES[ap] ?? {
      label: ap,
      className: "border-border bg-panel text-ink-soft",
    };
  return <span className={`${CHIP} ${style.className}`}>{style.label}</span>;
}

export function StatusPill({ status }: { status: string }) {
  const map: Record<string, { label: string; className: string }> = {
    needs_review: {
      label: "Needs Review",
      className: "border-warn-line bg-warn-soft text-warn",
    },
    returned: {
      label: "Returned",
      className: "border-border-strong bg-sunken text-ink-soft",
    },
    approved: {
      label: "Approved",
      className: "border-ok-line bg-ok-soft text-ok",
    },
  };
  const style =
    map[status] ?? { label: status, className: "border-border bg-panel text-ink-soft" };
  return <span className={`${CHIP} ${style.className}`}>{style.label}</span>;
}

export function Button({
  children,
  variant = "secondary",
  className = "",
  ...rest
}: {
  children: ReactNode;
  variant?: "primary" | "secondary" | "ghost";
  className?: string;
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  const base =
    "inline-flex items-center justify-center gap-2 rounded-md px-3.5 py-2 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50";
  const styles = {
    // Solid fill is the button's own signal - nothing else in the app
    // uses a solid accent fill.
    primary: "bg-accent text-accent-ink hover:bg-accent-hover",
    secondary:
      "border border-border-strong bg-panel text-ink hover:border-accent hover:text-accent",
    ghost: "text-ink-soft hover:bg-panel-hover hover:text-ink",
  };
  return (
    <button className={`${base} ${styles[variant]} ${className}`} {...rest}>
      {children}
    </button>
  );
}

export function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-label font-semibold text-ink-soft">{label}</span>
      {children}
    </label>
  );
}

/*
  Focus is handled globally by the :focus-visible ring in globals.css.
  These keep a border-colour change as a second, redundant cue, but the
  ring is what actually makes focus visible - a border shifting from
  #b9c4cf to the accent on an input that already had a border was close
  to imperceptible, which is how the old inputs failed WCAG 2.4.7 in
  practice while technically "having" a focus style.
*/
const inputClass =
  "w-full rounded-md border border-border-strong bg-panel px-2.5 py-2 text-body text-ink placeholder:text-ink-faint focus:border-accent";

export function TextInput(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input className={inputClass} {...props} />;
}

export function TextArea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={inputClass} {...props} />;
}

export function Select({
  children,
  ...rest
}: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select className={inputClass} {...rest}>
      {children}
    </select>
  );
}

/**
 * A finding, with its own icon.
 *
 * The icon comes from the tone rather than being typed into each
 * message. Callers used to prefix their own text with a bare ✓, ⚠ or ~,
 * which meant the glyph could disagree with the tone, sat on the text
 * baseline instead of aligning with the first line, and rendered as a
 * different shape per platform.
 */
export function Callout({
  tone,
  children,
}: {
  tone: "ok" | "warn" | "crit" | "accent";
  children: ReactNode;
}) {
  const styles = {
    ok: "border-ok-line bg-ok-soft text-ok",
    warn: "border-warn-line bg-warn-soft text-warn",
    crit: "border-crit-line bg-crit-soft text-crit",
    accent: "border-accent-line bg-accent-soft text-accent-strong",
  };
  const Glyph = tone === "ok" ? IconCheck : IconAlert;
  return (
    <div
      className={`flex items-start gap-2 rounded-md border px-3 py-2.5 text-sm ${styles[tone]}`}
    >
      <Glyph size={15} className="mt-[3px] shrink-0" />
      <div className="min-w-0">{children}</div>
    </div>
  );
}

/**
 * A placeholder shaped like the thing that is loading.
 *
 * Deliberately not a spinner. These pages fetch five endpoints in
 * parallel and wait on the slowest - measured at ~1.6s against the
 * deployed API - so the wait is long enough to need filling but short
 * enough that a centred spinner just flashes. A skeleton that matches
 * the real layout fills it without moving anything when the data lands:
 * same tile grid, same panel heights, no reflow.
 *
 * The pulse is CSS animation, so the prefers-reduced-motion guard in
 * globals.css already stops it for anyone who asked for that.
 */
export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div className={`animate-pulse rounded bg-sunken ${className}`} aria-hidden />
  );
}

export function Spinner() {
  return (
    <div className="flex items-center gap-2 text-sm text-ink-soft">
      <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-border-strong border-t-accent" />
      Loading…
    </div>
  );
}

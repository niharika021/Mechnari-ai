import type { ReactNode } from "react";

export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-[10px] border border-border bg-surface ${className}`}
    >
      {children}
    </div>
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
    tone === "crit" ? "text-crit" : tone === "accent" ? "text-accent-strong" : "text-ink";
  return (
    <Card className="px-4 pb-3 pt-3.5">
      <div className="font-mono text-[10.5px] uppercase tracking-wider text-ink-faint">
        {label}
      </div>
      <div className={`font-display text-[1.7rem] font-bold leading-tight ${valueColor}`}>
        {value}
      </div>
      {hint ? <div className="mt-1 font-mono text-xs text-ink-soft">{hint}</div> : null}
    </Card>
  );
}

const AP_STYLES: Record<string, { label: string; className: string }> = {
  H: { label: "High", className: "bg-crit-soft text-crit border-crit" },
  M: { label: "Medium", className: "bg-warn-soft text-warn border-warn" },
  L: { label: "Low", className: "bg-ok-soft text-ok border-ok" },
};

export function ApBadge({ ap }: { ap: string }) {
  const style = AP_STYLES[ap] ?? { label: ap, className: "bg-surface text-ink-soft border-border" };
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 font-mono text-[10.5px] font-semibold uppercase tracking-wide ${style.className}`}
    >
      {style.label}
    </span>
  );
}

export function StatusPill({ status }: { status: string }) {
  const map: Record<string, { label: string; className: string }> = {
    needs_review: { label: "Needs Review", className: "bg-warn-soft text-warn border-warn" },
    returned: { label: "Returned", className: "bg-surface-hover text-ink-soft border-border-strong" },
    approved: { label: "Approved", className: "bg-ok-soft text-ok border-ok" },
  };
  const style = map[status] ?? { label: status, className: "bg-surface text-ink-soft border-border" };
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 font-mono text-[10.5px] font-semibold uppercase tracking-wide ${style.className}`}
    >
      {style.label}
    </span>
  );
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
    "rounded-lg px-4 py-2.5 font-semibold text-sm transition-[filter,transform] active:scale-[.99] disabled:opacity-50 disabled:cursor-not-allowed";
  const styles = {
    primary: "bg-accent text-accent-ink hover:brightness-110",
    secondary:
      "bg-transparent text-ink border border-border-strong hover:border-accent hover:text-accent-strong",
    ghost: "bg-transparent text-ink-soft hover:text-ink",
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
    <label className="flex flex-col gap-1.5">
      <span className="text-[12.5px] font-semibold text-ink-soft">{label}</span>
      {children}
    </label>
  );
}

const inputClass =
  "rounded-[7px] border border-border-strong bg-bg-elevated px-3 py-2 text-sm text-ink placeholder:text-ink-faint focus:border-accent focus:outline-none";

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

export function Callout({
  tone,
  children,
}: {
  tone: "ok" | "warn" | "crit" | "accent";
  children: ReactNode;
}) {
  const styles = {
    ok: "bg-ok-soft border-ok text-ok",
    warn: "bg-warn-soft border-warn text-warn",
    crit: "bg-crit-soft border-crit text-crit",
    accent: "bg-accent-soft border-accent-line text-accent-strong",
  };
  return (
    <div className={`rounded-[9px] border px-4 py-3 text-sm ${styles[tone]}`}>
      {children}
    </div>
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

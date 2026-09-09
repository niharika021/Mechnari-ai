"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { SignIn } from "@/components/SignIn";

const ROLES = [
  { href: "/design", icon: "\u{1F6E0}\u{FE0F}", label: "Design Engineer" },
  { href: "/quality", icon: "\u{1F50D}", label: "Quality Engineer" },
  { href: "/company", icon: "\u{1F4CA}", label: "Company & Leadership" },
] as const;

export function RoleNav() {
  const pathname = usePathname();

  return (
    <>
      <div className="mb-[22px] rounded-[10px] border border-border border-l-4 border-l-accent bg-gradient-to-br from-surface to-bg-elevated px-6 py-5">
        <div className="font-mono text-[11px] uppercase tracking-[0.12em] text-accent">
          Enterprise DFMEA Risk Copilot
        </div>
        <h1 className="mt-1.5 font-display text-[1.65rem] font-bold text-ink">
          Mechnari.ai — Grounded in Your Own Warranty History
        </h1>
        <p className="mt-2 max-w-[74ch] text-sm leading-relaxed text-ink-soft">
          Three views of the same deterministic core - Design Engineer, Quality
          Engineer, and Company &amp; Leadership - because drafting, auditing and
          reporting on risk are different jobs.
        </p>
      </div>

      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
      <nav className="flex w-fit gap-1 rounded-[10px] border border-border bg-surface p-1">
        {ROLES.map((role) => {
          const active = pathname?.startsWith(role.href);
          return (
            <Link
              key={role.href}
              href={role.href}
              className={`flex items-center gap-2 rounded-[7px] px-4 py-2.5 text-sm font-semibold transition-colors ${
                active
                  ? "bg-accent-soft text-accent-strong"
                  : "text-ink-soft hover:text-ink"
              }`}
            >
              <span aria-hidden>{role.icon}</span>
              {role.label}
            </Link>
          );
        })}
      </nav>
        <SignIn />
      </div>
    </>
  );
}

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { SignIn } from "@/components/SignIn";
import { ThemeToggle } from "@/components/ThemeToggle";
import {
  IconChart,
  IconClipboardCheck,
  IconDrafting,
} from "@/components/icons";

const ROLES = [
  { href: "/design", Icon: IconDrafting, label: "Design", full: "Design Engineer" },
  { href: "/quality", Icon: IconClipboardCheck, label: "Quality", full: "Quality Engineer" },
  { href: "/company", Icon: IconChart, label: "Program", full: "Company & Leadership" },
] as const;

/**
 * The application bar.
 *
 * What this replaces: a 197px marketing hero card - eyebrow, tagline
 * headline, value-proposition paragraph - re-rendered on every page
 * load, with the role tabs below it at `position: static` so the only
 * navigation in the app scrolled away. Measured on the deployed site,
 * the first control an engineer could touch sat 617px down a 698px
 * viewport: 88% of the first screen spent before any work could start.
 *
 * A design engineer opens this several times a day. They do not need to
 * be told what the product is; they need to reach the form. So the
 * pitch is gone from the working views entirely, and the bar is sticky,
 * 52px, and carries only what is needed to move and to sign in.
 *
 * The role labels shorten to one word ("Design", "Quality", "Program")
 * with the full title in `title`. Three four-word tabs was a line of
 * text pretending to be navigation.
 */
export function RoleNav() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-panel/95 backdrop-blur-sm">
      <div className="mx-auto flex h-[52px] max-w-[1240px] items-center gap-4 px-6">
        <Link
          href="/design"
          className="flex shrink-0 items-center gap-2"
          title="Mechnari.ai — DFMEA risk copilot"
        >
          {/* The mark: a severity bar stepping up. It means something
              here rather than being a decorative glyph. */}
          <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden focusable="false">
            <rect x="3" y="14" width="4" height="7" rx="1" fill="var(--color-ok)" />
            <rect x="10" y="9" width="4" height="12" rx="1" fill="var(--color-warn)" />
            <rect x="17" y="3" width="4" height="18" rx="1" fill="var(--color-crit)" />
          </svg>
          <span className="font-display text-lg font-bold tracking-tight text-ink">
            Mechnari
          </span>
        </Link>

        <nav className="flex items-center gap-0.5" aria-label="Role views">
          {ROLES.map(({ href, Icon, label, full }) => {
            const active = pathname?.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                title={full}
                aria-current={active ? "page" : undefined}
                className={`flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm font-semibold transition-colors ${
                  active
                    ? "bg-accent-soft text-accent-strong"
                    : "text-ink-soft hover:bg-panel-hover hover:text-ink"
                }`}
              >
                <Icon size={15} />
                {label}
              </Link>
            );
          })}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <ThemeToggle />
          <SignIn />
        </div>
      </div>
    </header>
  );
}

/**
 * The per-view header that replaced each page's h2-plus-paragraph.
 *
 * `purpose` is capped at one short line on purpose. The design view used
 * to open with an 85-word paragraph explaining what Mechnari does to a
 * part; that belongs where someone is deciding whether to trust the
 * tool, not above a form they use daily. Long-form explanation moved
 * into the empty states, which is where it is actually read.
 */
export function PageHeader({
  title,
  purpose,
  actions,
}: {
  title: string;
  purpose: string;
  actions?: React.ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-2 pb-1">
      <div>
        <h1 className="font-display text-title font-bold tracking-tight text-ink">
          {title}
        </h1>
        <p className="mt-0.5 text-sm text-ink-faint">{purpose}</p>
      </div>
      {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
    </div>
  );
}

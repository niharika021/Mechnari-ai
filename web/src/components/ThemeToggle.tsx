"use client";

import { useEffect, useState } from "react";
import { IconMoon, IconSun } from "@/components/icons";

const KEY = "mechnari-theme";

/**
 * Light/dark toggle.
 *
 * Three states, not two, and that distinction is the whole reason this
 * is more than a boolean: "system" means no `data-theme` attribute at
 * all, so `prefers-color-scheme` decides. Stamping `light` on the root
 * to represent "system, currently light" would freeze the page against
 * the OS switching later in the day.
 *
 * Every localStorage access is wrapped. It throws outright in some
 * contexts - a private window with site data blocked, a thumbnailer -
 * and a theme button is not worth taking the page down for.
 */
export function ThemeToggle() {
  const [theme, setTheme] = useState<"light" | "dark" | null>(null);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(KEY);
      if (stored === "light" || stored === "dark") {
        setTheme(stored);
        document.documentElement.setAttribute("data-theme", stored);
      }
    } catch {
      /* No stored preference available; system setting stands. */
    }
  }, []);

  // Which icon to show: the one for the theme the click would move to.
  // Resolve "system" against the media query so the button never offers
  // to switch to the mode already on screen.
  const resolved =
    theme ??
    (typeof window !== "undefined" &&
    window.matchMedia?.("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light");
  const next = resolved === "dark" ? "light" : "dark";

  function apply() {
    setTheme(next);
    const root = document.documentElement;
    root.setAttribute("data-theme", next);

    /*
      Force a full style recalculation.

      This looks like superstition and is not. Changing data-theme
      redefines the --color-* tokens on :root, and elements that DECLARE
      a colour pick the new value up, but elements that only INHERIT one
      keep the old computed value: Chrome does not invalidate the
      inherited substitution through the subtree. Measured after a
      toggle from dark to light, with no forced recalc: the ground went
      to rgb(243,246,249) while <main> stayed at rgb(232,230,224) - the
      dark ink - so every heading beneath it rendered light-on-light at
      a contrast ratio of 1.15. Cloning an affected node into <body>
      rendered it correctly, which is what identified this as
      invalidation rather than a cascade problem.

      Detaching the root for one frame is the reliable way to make the
      engine rebuild the whole tree's computed styles. It costs a single
      synchronous reflow on a deliberate, infrequent user action, which
      is a fair price for the alternative being unreadable text.

      Page LOADS do not depend on this - the theme is stamped before
      first paint by the inline script in layout.tsx, so there is no
      mutation to invalidate there. This covers the click only.
    */
    const prev = root.style.display;
    root.style.display = "none";
    void root.offsetHeight;
    root.style.display = prev;

    try {
      localStorage.setItem(KEY, next);
    } catch {
      /* Preference won't survive a reload; the toggle still works now. */
    }
  }

  return (
    <button
      type="button"
      onClick={apply}
      title={`Switch to ${next} theme`}
      aria-label={`Switch to ${next} theme`}
      className="flex h-8 w-8 items-center justify-center rounded-md text-ink-faint transition-colors hover:bg-panel-hover hover:text-ink"
    >
      {next === "dark" ? <IconMoon size={15} /> : <IconSun size={15} />}
    </button>
  );
}

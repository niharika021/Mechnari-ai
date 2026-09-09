import type { SVGProps } from "react";

/**
 * The icon set.
 *
 * These replace emoji. Emoji were doing icon duty in the primary
 * navigation and on primary buttons, and they fail at it in three ways
 * that matter for a tool whose output is an audit record: they render as
 * a different picture on every operating system, they cannot inherit
 * `currentColor` so they never match the text beside them, and they
 * carry a cartoon weight that undercuts the seriousness of the content.
 *
 * All of them are drawn on a 24-unit grid with a 1.6 stroke and no fill,
 * so they sit at the same optical weight as IBM Plex Sans at 13-14px.
 * `currentColor` throughout: an icon inside a button takes the button's
 * text colour automatically, including in dark mode and on hover, with
 * no per-icon colour rules anywhere.
 *
 * Hand-authored rather than pulled from a library. The whole set is
 * under 3KB and the CSP on this deployment blocks stylesheet and font
 * loads from anywhere but Google Fonts, so an icon-font dependency would
 * have been a silent-failure risk for no benefit.
 *
 * `aria-hidden` is the default: every icon here sits next to its own
 * text label, so announcing it would just repeat that label. Pass
 * `aria-hidden={false}` with a `<title>` if one ever stands alone.
 */

type IconProps = SVGProps<SVGSVGElement> & { size?: number };

function Icon({ size = 16, children, ...rest }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.6}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      focusable="false"
      {...rest}
    >
      {children}
    </svg>
  );
}

/** Design Engineer - drafting compass. */
export function IconDrafting(props: IconProps) {
  return (
    <Icon {...props}>
      <circle cx="12" cy="4.2" r="1.8" />
      <path d="M11 5.9 5.5 20M13 5.9 18.5 20" />
      <path d="M8.6 14.2h6.8" />
    </Icon>
  );
}

/** Quality Engineer - clipboard with a check. */
export function IconClipboardCheck(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M9 4.5H7.5A1.5 1.5 0 0 0 6 6v13a1.5 1.5 0 0 0 1.5 1.5h9A1.5 1.5 0 0 0 18 19V6a1.5 1.5 0 0 0-1.5-1.5H15" />
      <rect x="9" y="2.8" width="6" height="3.4" rx="1" />
      <path d="m9.4 13.4 2 2 3.4-3.9" />
    </Icon>
  );
}

/** Company & Leadership - bar chart. */
export function IconChart(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M4 20h16" />
      <path d="M7.5 20v-6M12 20V7M16.5 20v-9" />
    </Icon>
  );
}

/** A document already on file. */
export function IconDocument(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M13.5 3H7.5A1.5 1.5 0 0 0 6 4.5v15A1.5 1.5 0 0 0 7.5 21h9a1.5 1.5 0 0 0 1.5-1.5V7.5Z" />
      <path d="M13.5 3v4.5H18" />
      <path d="M9.2 12.5h5.6M9.2 16h5.6" />
    </Icon>
  );
}

/** Run the analysis. */
export function IconRun(props: IconProps) {
  return (
    <Icon {...props}>
      <circle cx="12" cy="12" r="8.6" />
      <path d="M10.4 9.1l5 2.9-5 2.9z" />
    </Icon>
  );
}

/** Send onward - to the Quality queue. */
export function IconSend(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M20 4 3.8 10.4l5.5 2.3z" />
      <path d="M20 4l-2.6 15.4-8.1-6.7z" />
    </Icon>
  );
}

/** A satisfied check - an audit that passed. */
export function IconCheck(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="m4.8 12.6 4.6 4.6L19.2 7.4" />
    </Icon>
  );
}

/** A finding that needs attention. */
export function IconAlert(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M12 3.8 21.2 20H2.8z" />
      <path d="M12 9.6v4.6" />
      <circle cx="12" cy="17.1" r=".9" fill="currentColor" stroke="none" />
    </Icon>
  );
}

export function IconChevronDown(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="m6 9.5 6 6 6-6" />
    </Icon>
  );
}

export function IconSun(props: IconProps) {
  return (
    <Icon {...props}>
      <circle cx="12" cy="12" r="4.2" />
      <path d="M12 2.6v2.2M12 19.2v2.2M2.6 12h2.2M19.2 12h2.2M5.4 5.4l1.6 1.6M17 17l1.6 1.6M18.6 5.4 17 7M7 17l-1.6 1.6" />
    </Icon>
  );
}

export function IconMoon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M20 14.4A8.4 8.4 0 0 1 9.6 4a8.4 8.4 0 1 0 10.4 10.4Z" />
    </Icon>
  );
}

export function IconDownload(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M12 3.8v10.4" />
      <path d="m7.8 10.4 4.2 3.8 4.2-3.8" />
      <path d="M4.6 18.4h14.8" />
    </Icon>
  );
}

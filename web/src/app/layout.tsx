import type { Metadata } from "next";
import { Archivo, IBM_Plex_Mono, IBM_Plex_Sans } from "next/font/google";
import "@copilotkit/react-ui/v2/styles.css";
import "./globals.css";
import { RoleNav } from "@/components/RoleNav";
import { AuthProvider } from "@/lib/auth";
import { CopilotProvider } from "@/components/CopilotProvider";
import { MechnariCopilot } from "@/components/MechnariCopilot";

const archivo = Archivo({
  variable: "--font-archivo",
  subsets: ["latin"],
  weight: ["500", "600", "700"],
});

const plexSans = IBM_Plex_Sans({
  variable: "--font-plex-sans",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

const plexMono = IBM_Plex_Mono({
  variable: "--font-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

export const metadata: Metadata = {
  title: "Mechnari.ai",
  description:
    "Enterprise AI DFMEA Risk Copilot - three role views over one deterministic core.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={`${archivo.variable} ${plexSans.variable} ${plexMono.variable}`}
    >
      <head>
        {/*
          Stamp the saved theme before first paint.

          Two reasons, and the second one is why this is not optional.

          The obvious one: applying a theme from a useEffect means the
          page paints in the OS theme first and then flips, so a user who
          chose light on a dark machine sees a dark flash on every load.

          The one that actually forced this: stamping data-theme AFTER
          paint left inherited colour stale. With the attribute set by
          React, <body> recomputed (it has its own `color` declaration)
          but <main> did not - it inherits, nothing declares colour on
          it, and Chrome did not invalidate the subtree. Measured: body
          rgb(232,230,224) on a dark ground, main rgb(23,28,34), with
          zero CSS rules matching main. Every heading under it inherited
          the light ink and rendered at a contrast ratio of 1.06 -
          invisible. Cloning the same node into <body> rendered it
          correctly, which is what pinned it to invalidation rather than
          the cascade.

          Setting the attribute before any of it is parsed means there is
          no mutation to invalidate, so the question never arises.

          Wrapped in try/catch: localStorage throws outright in a private
          window with site data blocked, and a theme preference is not
          worth a blank page. No preference simply leaves the attribute
          off, which is the "system" state prefers-color-scheme handles.
        */}
        <script
          dangerouslySetInnerHTML={{
            __html: `try{var t=localStorage.getItem("mechnari-theme");if(t==="dark"||t==="light"){document.documentElement.setAttribute("data-theme",t)}}catch(e){}`,
          }}
        />
      </head>
      <body className="min-h-screen bg-ground text-ink antialiased">
        {/* Client wrapper around CopilotKit's provider: it relays to the
            AG-UI endpoint on the FastAPI service, and surfaces stream
            errors, which the sidebar itself renders silently. */}
        <AuthProvider>
        <CopilotProvider>
          {/* The bar spans the viewport and holds its own inner max-width,
              so its bottom border runs edge to edge while its contents stay
              aligned with the content column below. A sticky element inside
              the padded column would have stuck to the column instead. */}
          <RoleNav />
          <main className="mx-auto max-w-[1240px] px-6 pb-20 pt-6">
            {children}
          </main>
          <MechnariCopilot />
        </CopilotProvider>
        </AuthProvider>
      </body>
    </html>
  );
}

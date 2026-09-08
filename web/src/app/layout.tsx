import type { Metadata } from "next";
import { Archivo, IBM_Plex_Mono, IBM_Plex_Sans } from "next/font/google";
import "./globals.css";
import { RoleNav } from "@/components/RoleNav";
import { CopilotChat } from "@/components/CopilotChat";

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
      <body className="min-h-screen bg-bg text-ink antialiased">
        <div className="mx-auto max-w-[1240px] px-6 pb-16 pt-6">
          <RoleNav />
          {children}
        </div>
        <CopilotChat />
      </body>
    </html>
  );
}

/**
 * The design engineer's own reports, kept in the browser.
 *
 * This is deliberately separate from the review queue on the server. A
 * report here is the engineer's working copy - generated, actions being
 * worked, not yet anybody else's business. It becomes shared only when it
 * is sent to Quality, which writes to the backend queue.
 *
 * Why localStorage and not the API: on Cloud Run the backend's filesystem
 * resets on scale-to-zero, so a server-side working copy is *less*
 * durable than this one for a single engineer. The honest limits are that
 * it is per-browser - it will not follow anyone to another machine, and
 * it is not a shared record. Firestore is the real answer; this is not
 * pretending otherwise.
 *
 * Every read and write is guarded: storage throws outright in some
 * contexts (private windows, blocked site data, thumbnail capture), and a
 * report list is not worth taking the page down for.
 */

import type { SheetResult } from "@/lib/api";

const KEY = "mechnari.reports.v1";

export type StoredReport = {
  id: string;
  createdAt: string;
  updatedAt: string;
  title: string;
  systemPackage: string;
  partCount: number;
  rowCount: number;
  /** Set once sent to Quality, with the draft ids it became. */
  submittedAt: string | null;
  draftIds: string[];
  result: SheetResult;
};

export type ReportSummary = Omit<StoredReport, "result">;

function readAll(): StoredReport[] {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as StoredReport[]) : [];
  } catch {
    // Corrupt or unavailable: behave as if there are no reports rather
    // than throwing on render.
    return [];
  }
}

function writeAll(reports: StoredReport[]): boolean {
  try {
    localStorage.setItem(KEY, JSON.stringify(reports));
    return true;
  } catch {
    // Quota or blocked storage. The caller keeps working in memory; it
    // just will not survive a reload, and saying so is better than
    // silently pretending it saved.
    return false;
  }
}

function newId(): string {
  const stamp = Date.now().toString(36).toUpperCase();
  const rand = Math.random().toString(36).slice(2, 6).toUpperCase();
  return `RPT-${stamp}-${rand}`;
}

export function listReports(): ReportSummary[] {
  return readAll()
    .map(({ result: _result, ...summary }) => summary)
    .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
}

export function getReport(id: string): StoredReport | null {
  return readAll().find((r) => r.id === id) ?? null;
}

export function saveNewReport(
  result: SheetResult,
  systemPackage: string,
): StoredReport {
  const now = new Date().toISOString();
  const first = result.items[0];
  const title =
    result.items.length > 1
      ? `${result.items.length} parts — ${systemPackage}`
      : `${first?.part_number ? first.part_number + " · " : ""}${
          first?.item_interface || "Untitled part"
        }`;
  const report: StoredReport = {
    id: newId(),
    createdAt: now,
    updatedAt: now,
    title,
    systemPackage,
    partCount: result.items.length,
    rowCount: result.total_rows,
    submittedAt: null,
    draftIds: [],
    result,
  };
  writeAll([report, ...readAll()]);
  return report;
}

export function updateReport(
  id: string,
  patch: Partial<Pick<StoredReport, "result" | "submittedAt" | "draftIds">>,
): StoredReport | null {
  const all = readAll();
  const index = all.findIndex((r) => r.id === id);
  if (index === -1) return null;
  const updated: StoredReport = {
    ...all[index],
    ...patch,
    rowCount: patch.result ? patch.result.total_rows : all[index].rowCount,
    updatedAt: new Date().toISOString(),
  };
  all[index] = updated;
  writeAll(all);
  return updated;
}

export function deleteReport(id: string): void {
  writeAll(readAll().filter((r) => r.id !== id));
}

/** Whether storage is usable at all, so the UI can say so honestly. */
export function storageAvailable(): boolean {
  try {
    const probe = "__mechnari_probe__";
    localStorage.setItem(probe, "1");
    localStorage.removeItem(probe);
    return true;
  } catch {
    return false;
  }
}

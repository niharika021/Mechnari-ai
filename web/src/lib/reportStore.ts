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

import { api, ApiError, type SheetResult } from "@/lib/api";

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

export function titleFor(result: SheetResult, systemPackage: string): string {
  const first = result.items[0];
  return result.items.length > 1
    ? `${result.items.length} parts — ${systemPackage}`
    : `${first?.part_number ? first.part_number + " · " : ""}${
        first?.item_interface || "Untitled part"
      }`;
}

export function saveNewReport(
  result: SheetResult,
  systemPackage: string,
): StoredReport {
  const now = new Date().toISOString();
  const title = titleFor(result, systemPackage);
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


/* ------------------------------------------------------------------ *
 * Signed in: the server. Signed out: this browser.
 *
 * Two stores, one interface, and the caller is told which it got rather
 * than left to guess. Signed in, reports live in Firestore with an owner
 * and follow the engineer between machines. Signed out there is no answer
 * to "whose report is this", so they stay in localStorage - writing
 * owner-less rows into a shared database would make them nobody's and
 * everybody's at once.
 *
 * If the server is unreachable while signed in, these fall back to local
 * storage rather than failing. Losing a week of DFMEA work to a network
 * blip is worse than a report that is temporarily only on one machine.
 * ------------------------------------------------------------------ */

export type AnyReportSummary = ReportSummary & { remote: boolean; ownerName?: string };

function fromServer(r: {
  id: string;
  title: string;
  system_package: string;
  part_count: number;
  row_count: number;
  created_at: string;
  updated_at: string;
  submitted_at: string | null;
  draft_ids: string[];
  owner_name?: string;
}): AnyReportSummary {
  return {
    id: r.id,
    createdAt: r.created_at,
    updatedAt: r.updated_at,
    title: r.title,
    systemPackage: r.system_package,
    partCount: r.part_count,
    rowCount: r.row_count,
    submittedAt: r.submitted_at,
    draftIds: r.draft_ids ?? [],
    remote: true,
    ownerName: r.owner_name,
  };
}

export async function listAll(signedIn: boolean): Promise<AnyReportSummary[]> {
  const local = listReports().map((r) => ({ ...r, remote: false }));
  if (!signedIn) return local;
  try {
    const remote = (await api.listReports()).map(fromServer);
    // Local ones are still shown when signed in - they were made before
    // signing in and hiding them would look like data loss.
    return [...remote, ...local].sort((a, b) =>
      b.updatedAt.localeCompare(a.updatedAt),
    );
  } catch {
    return local;
  }
}

export async function loadReport(
  id: string,
  signedIn: boolean,
): Promise<{ report: StoredReport; remote: boolean } | null> {
  const local = getReport(id);
  if (local) return { report: local, remote: false };
  if (!signedIn) return null;
  try {
    const r = await api.getReport(id);
    return {
      report: { ...fromServer(r), result: r.result } as StoredReport,
      remote: true,
    };
  } catch {
    return null;
  }
}

export async function createReport(
  result: SheetResult,
  systemPackage: string,
  signedIn: boolean,
): Promise<{ id: string; remote: boolean }> {
  if (signedIn) {
    try {
      const created = await api.createReport({
        title: titleFor(result, systemPackage),
        system_package: systemPackage,
        result,
      });
      return { id: created.id, remote: true };
    } catch (err) {
      // A 401 means the token was rejected; anything else is a network or
      // server problem. Either way the work is kept locally.
      if (!(err instanceof ApiError)) {
        /* fall through */
      }
    }
  }
  return { id: saveNewReport(result, systemPackage).id, remote: false };
}

export async function persistResult(
  id: string,
  remote: boolean,
  result: SheetResult,
): Promise<void> {
  if (remote) {
    try {
      await api.updateReport(id, { result });
      return;
    } catch {
      // Keep a local copy so the edit is not simply lost.
      updateReport(id, { result });
      return;
    }
  }
  updateReport(id, { result });
}

export async function persistSubmission(
  id: string,
  remote: boolean,
  draftIds: string[],
): Promise<void> {
  const submittedAt = new Date().toISOString();
  if (remote) {
    try {
      await api.updateReport(id, { submitted_at: submittedAt, draft_ids: draftIds });
      return;
    } catch {
      updateReport(id, { submittedAt, draftIds });
      return;
    }
  }
  updateReport(id, { submittedAt, draftIds });
}

export async function removeReport(
  id: string,
  remote: boolean,
): Promise<void> {
  if (remote) {
    try {
      await api.deleteReport(id);
      return;
    } catch {
      /* fall through to the local delete */
    }
  }
  deleteReport(id);
}

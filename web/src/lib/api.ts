/**
 * Typed client for the Mechnari FastAPI backend (../../api.py).
 *
 * Every function here is a thin fetch wrapper - the backend does no more
 * computing than the Python engines it calls, and this file does no more
 * than give that JSON a shape TypeScript can check. All requests happen
 * from the browser (Next.js Server/Client components both run this fine
 * for the read side; mutations are called from Client Components so the
 * UI can react to the result without a full page reload).
 */

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new ApiError(res.status, detail?.detail ?? res.statusText);
  }
  return res.json() as Promise<T>;
}

export type Part = {
  part_id: string;
  system_package: string;
  item_reference: string;
  elementary_function: string;
  material_type: string;
  part_type_id: string;
  part_type_name: string;
  family_id: string;
  family_name: string;
  drawing_spec_ref: string;
  yield_strength_mpa: number;
  max_temp_limit_c: number;
};

export type PartType = {
  part_type_id: string;
  part_type_name: string;
  family_id: string;
  family_name: string;
  member_part_count: number;
};

export type CandidateRow = {
  mode_id: string;
  failure_mode: string;
  potential_cause: string;
  effect_description: string;
  severity: number;
  occurrence: number;
  detection: number;
  action_priority: "H" | "M" | "L";
  learned_from: string;
  evidence_ids: string;
  recommended_action: string;
  // Computed server-side by risk_engine.find_ap_levers and sent with the row.
  // Optional because drafts submitted before this field existed are still in
  // the queue file without it.
  levers?: ApLever[];
};

export type Neighbour = {
  part_id: string;
  item_reference: string;
  part_type_name: string;
  material_type: string;
  system_package: string;
  similarity: number;
};

export type Proposal =
  | {
      status: "success";
      reason: string;
      confident: boolean;
      confirmed: boolean;
      part_type_id: string;
      part_type_name: string;
      family_name: string;
      confidence: number;
      safety_candidates: number;
      neighbours: Neighbour[];
      candidates: CandidateRow[];
    }
  | { status: "no_match"; reason: string };

export type ApLever = {
  factor: "occurrence" | "detection";
  from: number;
  to: number;
  step: number;
  resulting_ap: "H" | "M" | "L";
};

export type ApLeverResult = { current_ap: "H" | "M" | "L"; levers: ApLever[] };

export type Draft = {
  draft_id: string;
  part_name: string;
  function: string;
  material: string;
  system_package: string;
  part_type_name: string;
  accepted_rows: CandidateRow[];
  declined_rows: CandidateRow[];
  submitted_by: string;
  submitted_at: string;
  status: "needs_review" | "returned" | "approved";
  review_comments: string;
  reviewed_at: string | null;
};

export type SeverityFinding = {
  part_id: string;
  failure_mode: string;
  severity: number;
  standard_severity: number;
  finding: string;
  effect_description: string;
};

export type OccurrenceFinding = {
  part_id: string;
  failure_mode: string;
  occurrence: number;
  derived_occurrence: number;
  finding: string;
  evidence_scope: "OWN_PART" | "TYPE_HISTORY";
  evidence_ids: string;
};

export type GapFinding = {
  part_id: string;
  item_reference: string;
  failure_mode: string;
  standard_severity: number;
  priority: string;
  learned_from: string;
  evidence_ids: string;
  system_package: string;
};

// One row of the AIAG-VDA DFMEA form sheet. Field names match the sheet's
// columns so the table renderer needs no translation layer.
export type SheetRow = {
  part_number: string;
  item_interface: string;
  elementary_function: string;
  material: string;
  system_package: string;

  failure_mode: string;
  potential_effect: string;
  system_level: string;
  severity: number;

  potential_cause: string;
  drawing_spec: string;
  pes: string;
  design_control_prevention: string;
  occurrence: number;

  detection_control: string;
  test_reference: string;
  detection: number;

  action_priority: "H" | "M" | "L";
  rpn_legacy: number;

  recommended_action: string;
  responsibility: string;
  target_completion_date: string;
  action_taken: string;
  completed_date: string;

  evidence_ids: string;
  learned_from: string;
  field_reports: number;
  field_claims: number;
  claims_per_1000: number | null;
  scope_level: string;
  mode_id: string;

  // Filled from the AP levers, not estimated - see dfmea_sheet.py.
  reassessed_severity: number;
  reassessed_occurrence: number;
  reassessed_detection: number;
  reassessed_action_priority: "H" | "M" | "L";
  reassessed_rpn: number;
  reassessment_basis: string;

  // Set once an engineer has reviewed the row. Absent on a raw proposal,
  // which is itself meaningful: a sheet without provenance has not been
  // through anybody's judgement.
  provenance?: "proposed" | "edited" | "engineer_added";
  occurrence_override_reason?: string;
  severity_dispute_note?: string;
};

export type DeclinedRow = {
  failure_mode: string;
  action_priority: "H" | "M" | "L";
  severity: number;
  reason: string;
};

export type SheetItemBlock = {
  status: "success" | "no_match" | "insufficient_input";
  reason?: string;
  part_number: string;
  item_interface?: string;
  part_type_id?: string;
  part_type_name?: string;
  family_name?: string;
  confidence?: number;
  confirmed?: boolean;
  confident?: boolean;
  type_reason?: string;
  safety_rows?: number;
  similar_parts?: Neighbour[];
  own_history?: IssueRecord[];
  rows: SheetRow[];
  // Present after review: rows the engineer left out, with the reason.
  // Kept so Quality can tell "considered and rejected" from "never
  // looked at" - the distinction a manual sheet loses.
  declined?: DeclinedRow[];
};

export type SheetResult = {
  items: SheetItemBlock[];
  total_rows: number;
  high_rows: number;
  safety_rows: number;
  rows_with_evidence: number;
  ap_table_verified: boolean;
};

export type SheetItemInput = {
  part_number?: string;
  description?: string;
  function?: string;
  material?: string;
  system_package?: string;
  part_type_id?: string;
  existing_part_id?: string;
};

// A row of the DFMEA already on file. Carries both readings: the numbers
// as filed (what somebody signed) and what the warranty record says now.
export type FiledRow = {
  mode_id: string;
  item_interface: string;
  elementary_function: string;
  failure_mode: string;
  potential_effect: string;
  potential_cause: string;
  design_control_prevention: string;
  recommended_action: string;

  severity: number;
  occurrence: number;
  detection: number;
  action_priority: "H" | "M" | "L";
  rpn_legacy: number;

  evidence_severity: number;
  evidence_occurrence: number;
  evidence_detection: number;
  evidence_action_priority: "H" | "M" | "L";
  disagrees: boolean;
  disagreement_notes: string;

  evidence_ids: string;
  evidence_scope: string;
  claims_per_1000: number | null;
  analyzed_by: string;
  analysis_date: string;
  revision: string;
};

export type ExistingDfmea = {
  status: "success";
  part_id: string;
  item_reference: string;
  elementary_function: string;
  material: string;
  system_package: string;
  part_type_name: string;
  family_name: string;
  drawing_spec: string;
  analyzed_by: string;
  analysis_date: string;
  revision: string;
  rows_analysed: number;
  rows_applicable: number;
  coverage_pct: number;
  rows_disagreeing: number;
  filed_rows: FiledRow[];
  missing_rows: GapFinding[];
  own_history: IssueRecord[];
  ap_table_verified: boolean;
};

export type IssueSummaryRow = {
  part_id: string;
  item_reference: string;
  issue_count: number;
  total_claims: number;
  latest_report: string;
};

export type IssueRecord = {
  issue_id: string;
  part_id: string;
  item_reference: string | null;
  mode_id: string;
  failure_mode: string | null;
  report_date: string;
  claim_count: number;
  units_in_service: number;
  claims_per_1000: number;
  detection_stage: string;
  observed_severity: number;
  description: string;
};

export type AuditResult = {
  part: Part | null;
  severity_findings: SeverityFinding[];
  occurrence_findings: OccurrenceFinding[];
  gaps: GapFinding[];
};

export type GapMetrics = {
  parts_analysed: number;
  modes_in_catalog: number;
  total_gaps: number;
  parts_with_gaps: number;
  safety_gaps: number;
  gaps_with_evidence: number;
  mean_coverage_pct: number;
  severity_drift_rows: number;
};

export type RiskMetrics = {
  worksheet_rows: number;
  rows_measured_on_own_part: number;
  occurrence_understated: number;
  occurrence_understated_own_part: number;
  occurrence_overstated: number;
  ap_high_as_filed: number;
  ap_high_evidence_based: number;
  ap_escalations: number;
  ap_table_verified: boolean;
};

export type BacktestSummary = {
  cutoff: string;
  incidents: number;
  knowable: number;
  unknowable: number;
  dfmea_recall: number;
  mechnari_recall: number;
  dfmea_recall_claim_weighted: number;
  mechnari_recall_claim_weighted: number;
  newly_caught: number;
  newly_caught_claims: number;
  newly_caught_cross_part: number;
  newly_caught_safety: number;
};

export type ColdStart = {
  parts_evaluated: number;
  failure_modes_evaluated: number;
  modes_surfaced: number;
  recall: number;
  parts_fully_covered: number;
  parts_missed_entirely: number;
  mean_proposed: number;
};

export const api = {
  parts: (systemPackage?: string) =>
    request<Part[]>(
      `/api/parts${systemPackage ? `?system_package=${encodeURIComponent(systemPackage)}` : ""}`,
    ),
  systemPackages: () => request<string[]>("/api/system-packages"),
  partTypes: () => request<PartType[]>("/api/part-types"),
  proposeDfmea: (body: {
    part_name: string;
    function: string;
    material: string;
    part_type_id?: string;
  }) =>
    request<Proposal>("/api/propose-dfmea", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  apLevers: (severity: number, occurrence: number, detection: number) =>
    request<ApLeverResult>("/api/ap-levers", {
      method: "POST",
      body: JSON.stringify({ severity, occurrence, detection }),
    }),
  submitDraft: (body: {
    part_name: string;
    function: string;
    material: string;
    system_package: string;
    part_type_name: string;
    accepted_rows: CandidateRow[];
    declined_rows: CandidateRow[];
    submitted_by?: string;
  }) =>
    request<{ draft_id: string }>("/api/queue/submit", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  queue: () => request<Draft[]>("/api/queue"),
  draft: (draftId: string) => request<Draft>(`/api/queue/${draftId}`),
  setDraftStatus: (draftId: string, status: Draft["status"], comments: string) =>
    request<{ ok: true }>(`/api/queue/${draftId}/status`, {
      method: "POST",
      body: JSON.stringify({ status, comments }),
    }),
  auditPart: (partId: string) => request<AuditResult>(`/api/audit/${partId}`),
  gaps: (systemPackage?: string) =>
    request<GapFinding[]>(
      `/api/gaps${systemPackage ? `?system_package=${encodeURIComponent(systemPackage)}` : ""}`,
    ),
  gapMetrics: () => request<GapMetrics>("/api/gap-metrics"),
  riskMetrics: () => request<RiskMetrics>("/api/risk-metrics"),
  backtest: (cutoff?: string) =>
    request<{ cutoff: string; summary: BacktestSummary; train_records: number; test_records: number }>(
      `/api/backtest${cutoff ? `?cutoff=${encodeURIComponent(cutoff)}` : ""}`,
    ),
  backtestSweep: () => request<BacktestSummary[]>("/api/backtest/sweep"),
  backtestCutoffs: () => request<{ cutoffs: string[]; default: string }>("/api/backtest/cutoffs"),
  coldStart: () => request<ColdStart>("/api/backtest/cold-start"),
  askCopilot: (question: string, sessionId: string) =>
    request<{ status: string; answer?: string; reason?: string }>("/api/copilot/ask", {
      method: "POST",
      body: JSON.stringify({ question, session_id: sessionId }),
    }),
  rescore: (rows: { severity: number; occurrence: number; detection: number }[]) =>
    request<{ action_priority: "H" | "M" | "L"; rpn_legacy: number; levers: ApLever[] }[]>(
      "/api/rescore",
      { method: "POST", body: JSON.stringify({ rows }) },
    ),
  existingDfmea: (partId: string) =>
    request<ExistingDfmea>(`/api/dfmea-sheet/${encodeURIComponent(partId)}`),
  dfmeaSheet: (items: SheetItemInput[]) =>
    request<SheetResult>("/api/dfmea-sheet", {
      method: "POST",
      body: JSON.stringify({ items }),
    }),
  copilotHealth: () =>
    request<{
      api_key_present: boolean;
      api_key_works: boolean;
      reason: string;
      agui_path: string;
    }>("/api/copilot/health"),
  issueSummary: () => request<IssueSummaryRow[]>("/api/issues/summary"),
  issuesForPart: (partId: string) =>
    request<IssueRecord[]>(`/api/issues/${encodeURIComponent(partId)}`),
  reload: () => request<{ ok: true }>("/api/reload", { method: "POST" }),
};

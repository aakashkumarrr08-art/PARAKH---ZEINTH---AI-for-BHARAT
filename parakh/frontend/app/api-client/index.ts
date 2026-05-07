export type TenderDocument = {
  document_id: string;
  filename: string;
  doc_type: string;
  relative_path: string;
  uploaded_at: string;
};

export type Tender = {
  _id: string;
  title: string;
  procuring_entity: string;
  bid_reference: string;
  description?: string | null;
  bid_validity_end?: string | null;
  status: string;
  documents: TenderDocument[];
  latest_manifest_id?: string | null;
  created_by?: string | null;
  created_at: string;
  updated_at: string;
};

export type EvidenceTemplate = {
  doc_name: string;
  doc_description?: string | null;
  required_fields: string[];
  required: boolean;
};

export type Criterion = {
  criterion_id: string;
  stage: string;
  factor: string;
  description: string;
  type: string;
  classification: string;
  mandatory: boolean;
  normalized_threshold: Record<string, unknown>;
  evidence_template: EvidenceTemplate[];
  guidance_notes?: string | null;
};

export type Manifest = {
  _id: string;
  tender_id: string;
  version: number;
  status: "DRAFT" | "APPROVED" | "SUPERSEDED";
  generated_from: string;
  source_documents: string[];
  criteria: Criterion[];
  approved_at?: string | null;
  approved_by?: string | null;
};

export type BidderDocument = {
  document_id: string;
  filename: string;
  doc_name: string;
  relative_path: string;
  content_type?: string | null;
  uploaded_at: string;
};

export type ChecklistItem = {
  doc_name: string;
  doc_description: string;
  doc_purpose: string;
  uploaded: boolean;
  document_id?: string | null;
  filename?: string | null;
};

export type Bidder = {
  _id: string;
  tender_id: string;
  name: string;
  bidder_type: "OEM" | "AUTHORIZED_BIDDER";
  oem_name?: string | null;
  documents: BidderDocument[];
  checklist_status: ChecklistItem[];
  overall_status: string;
  hard_disqualified: boolean;
  disqualification_reasons: string[];
  last_evaluated_at?: string | null;
};

export type ExtractedField = {
  name: string;
  value: unknown;
  confidence: number;
  source_text?: string | null;
  page_numbers: number[];
};

export type Evidence = {
  _id: string;
  tender_id: string;
  bidder_id: string;
  document_id: string;
  doc_name: string;
  filename: string;
  relative_path: string;
  extraction_method: string;
  text_preview: string;
  fields: ExtractedField[];
  overall_confidence: number;
};

export type EvidenceDocRef = {
  document_id: string;
  doc_name: string;
  filename: string;
  relative_path: string;
};

export type EvaluationEvent = {
  _id: string;
  tender_id: string;
  bidder_id: string;
  criterion_id: string;
  criterion_name: string;
  stage: string;
  criterion_type: string;
  classification: string;
  event_type: "AUTO_EVAL" | "OVERRIDE";
  sequence: number;
  evidence_docs: EvidenceDocRef[];
  extracted_values: Record<string, unknown>;
  evidence_quality: "HIGH" | "LOW";
  match_logic: string;
  auto_verdict: "Eligible" | "Not Eligible" | "Needs Manual Review";
  final_verdict: "Eligible" | "Not Eligible" | "Needs Manual Review";
  hard_disqualification_flags: string[];
  reason_code?: string | null;
  reviewer_id?: string | null;
  reviewer_notes?: string | null;
  prior_event_id?: string | null;
  event_hash: string;
  created_at: string;
};

export type EvaluationOverview = {
  tender_id: string;
  bidder_id: string;
  overall_status: string;
  hard_disqualified: boolean;
  disqualification_reasons: string[];
  latest_events: EvaluationEvent[];
};

export type DashboardStats = {
  tenders: number;
  bidders: number;
  disqualifications: number;
  evaluation_events: number;
  manual_overrides: number;
  auto_resolved: number;
};

export type AuditHistory = Record<string, EvaluationEvent[]>;

export type UserProfile = {
  _id: string;
  username: string;
  full_name: string;
  role: "ADMIN" | "OFFICER";
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api";
const BACKEND_ORIGIN = API_BASE.replace(/\/api$/, "");
const TOKEN_KEY = "parakh_demo_token";

function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

function setStoredToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token) {
    window.localStorage.setItem(TOKEN_KEY, token);
  } else {
    window.localStorage.removeItem(TOKEN_KEY);
  }
}

async function loginDemoOfficer(): Promise<string | null> {
  const form = new URLSearchParams();
  form.set("username", "officer");
  form.set("password", "officer123");
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form.toString()
  });
  if (!response.ok) {
    return null;
  }
  const payload = await response.json();
  setStoredToken(payload.access_token);
  return payload.access_token;
}

async function ensureToken(forceRefresh = false): Promise<string | null> {
  const existing = getStoredToken();
  if (existing && !forceRefresh) return existing;
  if (forceRefresh) {
    setStoredToken(null);
  }
  return loginDemoOfficer();
}

function buildHeaders(init?: RequestInit, token?: string | null): Headers {
  const headers = new Headers(init?.headers ?? {});
  if (!(init?.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  return headers;
}

function parseErrorMessage(errorText: string): string {
  try {
    const parsed = JSON.parse(errorText) as { detail?: string };
    return parsed.detail || errorText || "Request failed.";
  } catch {
    return errorText || "Request failed.";
  }
}

async function rawRequest(path: string, init?: RequestInit, forceRefresh = false): Promise<Response> {
  const token = await ensureToken(forceRefresh);
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: buildHeaders(init, token)
  });

  if (response.status === 401 && !forceRefresh) {
    return rawRequest(path, init, true);
  }

  return response;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await rawRequest(path, init);
  if (!response.ok) {
    throw new Error(parseErrorMessage(await response.text()));
  }
  return response.json() as Promise<T>;
}

async function requestBlob(path: string): Promise<Blob> {
  const response = await rawRequest(path);
  if (!response.ok) {
    throw new Error(parseErrorMessage(await response.text()));
  }
  return response.blob();
}

export function buildFileUrl(relativePath: string) {
  return `${BACKEND_ORIGIN}${relativePath}`;
}

export async function getProfile() {
  return request<UserProfile>("/auth/me");
}

export async function getDashboardStats() {
  return request<DashboardStats>("/audit/stats");
}

export async function getTenders() {
  return request<Tender[]>("/tenders");
}

export async function getTender(tenderId: string) {
  return request<Tender>(`/tenders/${tenderId}`);
}

export async function createTender(payload: {
  title: string;
  procuring_entity: string;
  bid_reference: string;
  description?: string;
  bid_validity_end?: string;
}) {
  return request<Tender>("/tenders", { method: "POST", body: JSON.stringify(payload) });
}

export async function uploadTenderDocument(tenderId: string, docType: string, file: File) {
  const form = new FormData();
  form.set("doc_type", docType);
  form.set("file", file);
  return request<Tender>(`/tenders/${tenderId}/documents`, { method: "POST", body: form });
}

export async function generateManifest(tenderId: string) {
  return request<Manifest>(`/tenders/${tenderId}/generate_manifest`, { method: "POST" });
}

export async function getLatestManifest(tenderId: string) {
  return request<Manifest>(`/tenders/${tenderId}/manifests/latest`);
}

export async function updateManifest(tenderId: string, manifestId: string, criteria: Criterion[]) {
  return request<Manifest>(`/tenders/${tenderId}/manifests/${manifestId}`, {
    method: "PUT",
    body: JSON.stringify({ criteria })
  });
}

export async function approveManifest(tenderId: string, manifestId: string) {
  return request<Manifest>(`/tenders/${tenderId}/manifests/${manifestId}/approve`, { method: "PUT" });
}

export async function getBidders(tenderId: string) {
  return request<Bidder[]>(`/tenders/${tenderId}/bidders`);
}

export async function createBidder(tenderId: string, payload: { name: string; bidder_type: "OEM" | "AUTHORIZED_BIDDER"; oem_name?: string }) {
  return request<Bidder>(`/tenders/${tenderId}/bidders`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function uploadBidderDocument(tenderId: string, bidderId: string, docName: string, file: File) {
  const form = new FormData();
  form.set("doc_name", docName);
  form.set("file", file);
  return request<Bidder>(`/tenders/${tenderId}/bidders/${bidderId}/documents`, {
    method: "POST",
    body: form
  });
}

export async function getBidderChecklist(tenderId: string, bidderId: string) {
  return request<ChecklistItem[]>(`/tenders/${tenderId}/bidders/${bidderId}/checklist`);
}

export async function ingestBidderDocs(tenderId: string, bidderId: string) {
  return request<Evidence[]>(`/tenders/${tenderId}/bidders/${bidderId}/ingest`, { method: "POST" });
}

export async function getEvidence(tenderId: string, bidderId: string) {
  return request<Evidence[]>(`/tenders/${tenderId}/bidders/${bidderId}/evidence`);
}

export async function evaluateBidder(tenderId: string, bidderId: string) {
  return request<EvaluationOverview>(`/evaluation/${tenderId}/${bidderId}`, { method: "POST" });
}

export async function getEvaluation(tenderId: string, bidderId: string) {
  return request<EvaluationOverview>(`/evaluation/${tenderId}/${bidderId}`);
}

export async function overrideCriterion(
  tenderId: string,
  bidderId: string,
  criterionId: string,
  payload: { final_verdict: "Eligible" | "Not Eligible" | "Needs Manual Review"; reason_code: string; reviewer_notes?: string }
) {
  return request<EvaluationOverview>(`/evaluation/${tenderId}/${bidderId}/${criterionId}/override`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function getReasonCodes() {
  return request<string[]>("/evaluation/metadata/reason-codes");
}

export async function getAuditHistory(tenderId: string, bidderId: string) {
  return request<AuditHistory>(`/audit/${tenderId}/${bidderId}`);
}

export async function downloadAuditReport(tenderId: string, bidderId: string, format: "xlsx" | "pdf") {
  const blob = await requestBlob(`/audit/${tenderId}/${bidderId}/export?format=${format}`);
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `parakh-audit-${bidderId}.${format}`;
  link.click();
  window.URL.revokeObjectURL(url);
}

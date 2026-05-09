/**
 * Dev: relative `/api` so Vite proxies to FastAPI (no wrong-port issues).
 * Override anytime with VITE_API_BASE_URL (e.g. deployed frontend → remote API).
 */
function resolveApiBaseUrl(): string {
  const explicit = import.meta.env.VITE_API_BASE_URL?.trim();
  if (explicit) {
    return explicit.replace(/\/+$/, "");
  }
  if (import.meta.env.DEV) {
    return "/api";
  }
  return "http://127.0.0.1:8000/api";
}

const API_BASE_URL = resolveApiBaseUrl();
/** Align with backend PROCESSING_TIMEOUT_SECONDS + Gemini retry backoff (default 10 min). */
const PROCESSING_TIMEOUT_MS = Number(import.meta.env.VITE_PROCESSING_TIMEOUT_MS ?? 600_000);

export interface UploadResponse {
  document_id: number;
  processing_status: string;
}

export interface ProcessResponse {
  document_id: number;
  processing_status: string;
  dashboard?: ProcessedDashboard;
  error?: string;
}

export interface BackendMetric {
  metric_name: string;
  current_year_value: number | null;
  previous_year_value: number | null;
  unit: string;
  source_page: number | null;
  source_text?: string;
  confidence_score: number;
}

export interface BackendRatio {
  ratio_name: string;
  value: number | null;
  unit: string;
  formula: string;
  inputs: Record<string, number | null>;
  missing_inputs: string[];
  explanation: string;
}

export interface BackendInsight {
  title: string;
  type: "positive" | "warning" | "risk" | "neutral";
  summary: string;
  supporting_metrics: string[];
  source_pages: number[];
  confidence_score: number;
}

export interface BackendSourceReference {
  page: number;
  label: string;
  snippet: string;
  confidence_score: number;
}

export interface ProcessedDashboard {
  document_id: number;
  file_name: string;
  company_name?: string | null;
  report_year?: number | null;
  parent_document_id?: number | null;
  processing_status: string;
  page_count: number;
  relevant_pages: number[];
  extracted_metrics: { metrics: BackendMetric[] };
  calculated_ratios: { ratios: BackendRatio[] };
  ai_insights: BackendInsight[];
  source_references: BackendSourceReference[];
  excel_download_path: string;
}

export interface DocumentSummary {
  document_id: number;
  file_name: string;
  processing_status: string;
  company_name?: string | null;
  report_year?: number | null;
}

export interface ComparisonPoint {
  document_id: number;
  report_year: number | null;
  value: number | null;
  source_page?: number | null;
  yoy_percent?: number | null;
  yoy_amount?: number | null;
}

export interface MetricSeriesRow {
  metric_name: string;
  unit: string;
  points: ComparisonPoint[];
}

export interface RatioSeriesRow {
  ratio_name: string;
  unit: string;
  points: ComparisonPoint[];
}

export interface ComparisonResponse {
  comparison_hash: string;
  documents: Array<{
    document_id: number;
    file_name: string;
    company_name: string | null;
    report_year: number | null;
  }>;
  metric_series: MetricSeriesRow[];
  ratio_series: RatioSeriesRow[];
  trend_summary: {
    headline: string;
    bullets: string[];
    confidence: number;
  };
  excel_download_path: string;
}

export function excelDownloadUrl(documentId: number) {
  return `${API_BASE_URL}/documents/${documentId}/export/excel/download`;
}

export function comparisonDownloadUrl(comparisonHash: string) {
  return `${API_BASE_URL}/documents/compare/download/${comparisonHash}`;
}

export async function uploadDocument(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/documents/upload`, {
    method: "POST",
    body: formData,
  });
  return parseJsonResponse(response);
}

export async function processDocument(documentId: number): Promise<ProcessResponse> {
  const response = await fetchWithTimeout(
    `${API_BASE_URL}/documents/${documentId}/process`,
    {
      method: "POST",
    },
    PROCESSING_TIMEOUT_MS,
  );
  return parseJsonResponse(response);
}

export async function getDashboard(documentId: number): Promise<ProcessedDashboard> {
  const response = await fetch(`${API_BASE_URL}/documents/${documentId}/dashboard`);
  return parseJsonResponse(response);
}

export async function listCompletedDocuments(): Promise<DocumentSummary[]> {
  const response = await fetch(`${API_BASE_URL}/documents/`);
  return parseJsonResponse(response);
}

export async function getRelatedDocuments(documentId: number): Promise<DocumentSummary[]> {
  const response = await fetch(`${API_BASE_URL}/documents/${documentId}/related`);
  return parseJsonResponse(response);
}

export async function compareDocuments(documentIds: number[]): Promise<ComparisonResponse> {
  const response = await fetchWithTimeout(
    `${API_BASE_URL}/documents/compare`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ document_ids: documentIds }),
    },
    PROCESSING_TIMEOUT_MS,
  );
  return parseJsonResponse(response);
}

async function parseJsonResponse<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof payload.detail === "string" ? payload.detail : "Request failed.";
    throw new Error(detail);
  }
  return payload as T;
}

async function fetchWithTimeout(
  input: RequestInfo | URL,
  init: RequestInit,
  timeoutMs: number,
): Promise<Response> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error(
        "Processing is taking longer than expected. The backend may still be working; check the server logs or try a smaller PDF.",
      );
    }
    throw error;
  } finally {
    window.clearTimeout(timeout);
  }
}

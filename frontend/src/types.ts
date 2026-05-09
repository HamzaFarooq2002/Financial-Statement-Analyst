export type InsightType = "positive" | "warning" | "risk" | "neutral";

export type ProcessingStepStatus = "complete" | "active" | "queued";
export type UploadWorkflowStatus = "idle" | "uploading" | "processing" | "completed" | "failed";

export interface ProcessingStep {
  label: string;
  status: ProcessingStepStatus;
  detail: string;
}

export interface FinancialMetric {
  metricName: string;
  currentYearValue: number | null;
  previousYearValue: number | null;
  unit: string;
  sourcePage: number | null;
  sourceText?: string;
  confidenceScore: number;
  tone: "good" | "watch" | "risk" | "neutral";
}

export interface RatioMetric {
  ratioName: string;
  value: number | null;
  unit: string;
  explanation: string;
  tone: "good" | "watch" | "risk" | "neutral";
}

export interface Insight {
  title: string;
  type: InsightType;
  summary: string;
  supportingMetrics: string[];
  sourcePages: number[];
  confidenceScore: number;
}

export interface Issue {
  title: string;
  severity: "high" | "medium" | "low";
  description: string;
  owner: string;
  sourcePage?: number;
}

export interface SourceReference {
  page: number;
  label: string;
  snippet: string;
  confidenceScore: number;
}

export interface TrustSummary {
  averageConfidence: number | null;
  sourcePageCount: number | null;
  openCheckCount: number | null;
}

export type DashboardViewMode = "single" | "compare";

export interface ComparisonDocumentMeta {
  document_id: number;
  file_name: string;
  company_name: string | null;
  report_year: number | null;
}

export interface ComparisonPointView {
  document_id: number;
  report_year: number | null;
  value: number | null;
  source_page?: number | null;
  yoy_percent?: number | null;
}

export interface MetricSeriesView {
  metric_name: string;
  unit: string;
  points: ComparisonPointView[];
}

export interface RatioSeriesView {
  ratio_name: string;
  unit: string;
  points: ComparisonPointView[];
}

export interface TrendSummaryView {
  headline: string;
  bullets: string[];
  confidence: number;
}

export interface ComparisonViewModel {
  comparison_hash: string;
  documents: ComparisonDocumentMeta[];
  metric_series: MetricSeriesView[];
  ratio_series: RatioSeriesView[];
  trend_summary: TrendSummaryView;
}

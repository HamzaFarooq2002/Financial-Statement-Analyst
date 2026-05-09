import { BarChart3, Bell, Building2, Gauge, Menu, Search, Settings } from "lucide-react";
import { useMemo, useState } from "react";
import {
  compareDocuments,
  comparisonDownloadUrl,
  excelDownloadUrl,
  getDashboard,
  processDocument,
  uploadDocument,
  type BackendMetric,
  type BackendRatio,
  type ComparisonResponse,
  type ProcessedDashboard,
} from "./api/client";
import { CustomerFocusPanel } from "./components/CustomerFocusPanel";
import { ExcelDownloadButton } from "./components/ExcelDownloadButton";
import { FinancialSnapshotCards } from "./components/FinancialSnapshotCards";
import { InsightPanel } from "./components/InsightPanel";
import { IssuesPanel } from "./components/IssuesPanel";
import { MultiYearComparisonPanel } from "./components/MultiYearComparisonPanel";
import { MultiYearSelector } from "./components/MultiYearSelector";
import { ProcessingStatus } from "./components/ProcessingStatus";
import { RatioAnalysisCards } from "./components/RatioAnalysisCards";
import { UploadPage } from "./components/UploadPage";
import type {
  DashboardViewMode,
  FinancialMetric,
  Insight,
  Issue,
  ProcessingStep,
  RatioMetric,
  SourceReference,
  TrustSummary,
  UploadWorkflowStatus,
} from "./types";

export default function App() {
  const [uploadedFile, setUploadedFile] = useState("Upload an annual report PDF");
  const [workflowStatus, setWorkflowStatus] = useState<UploadWorkflowStatus>("idle");
  const [errorMessage, setErrorMessage] = useState<string | undefined>();
  const [documentId, setDocumentId] = useState<number | null>(null);
  const [metrics, setMetrics] = useState<FinancialMetric[]>([]);
  const [ratios, setRatios] = useState<RatioMetric[]>([]);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [issues, setIssues] = useState<Issue[]>([]);
  const [sources, setSources] = useState<SourceReference[]>([]);
  const [dashboardViewMode, setDashboardViewMode] = useState<DashboardViewMode>("single");
  const [comparison, setComparison] = useState<ComparisonResponse | null>(null);
  const [compareBusy, setCompareBusy] = useState(false);
  const [processedCompanyName, setProcessedCompanyName] = useState<string | null>(null);
  const [processedReportYear, setProcessedReportYear] = useState<number | null>(null);

  const insightSnippetMap = useMemo(() => {
    const map = new Map<number, string>();
    for (const source of sources) {
      if (source.snippet && !map.has(source.page)) {
        map.set(source.page, source.snippet);
      }
    }
    return map;
  }, [sources]);

  const trustSummary = buildTrustSummary(metrics, sources, issues, workflowStatus);

  async function handleUpload(file: File) {
    setUploadedFile(file.name);
    setWorkflowStatus("uploading");
    setErrorMessage(undefined);
    setComparison(null);
    setDashboardViewMode("single");
    setProcessedCompanyName(null);
    setProcessedReportYear(null);

    try {
      const upload = await uploadDocument(file);
      setDocumentId(upload.document_id);
      setWorkflowStatus("processing");

      const processed = await processDocument(upload.document_id);
      if (processed.processing_status === "failed") {
        throw new Error(processed.error ?? "Document processing failed.");
      }

      const dashboard = processed.dashboard ?? (await getDashboard(upload.document_id));
      applyDashboard(dashboard);
      setWorkflowStatus("completed");
    } catch (error) {
      setWorkflowStatus("failed");
      setErrorMessage(error instanceof Error ? error.message : "Upload or processing failed.");
    }
  }

  async function handleCompare(documentIds: number[]) {
    setCompareBusy(true);
    setErrorMessage(undefined);
    try {
      const result = await compareDocuments(documentIds);
      setComparison(result);
      setDashboardViewMode("compare");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Comparison failed.");
    } finally {
      setCompareBusy(false);
    }
  }

  function applyDashboard(dashboard: ProcessedDashboard) {
    setUploadedFile(dashboard.file_name);
    setProcessedCompanyName(dashboard.company_name ?? null);
    setProcessedReportYear(dashboard.report_year ?? null);
    setMetrics(dashboard.extracted_metrics.metrics.map(mapMetric));
    setRatios(dashboard.calculated_ratios.ratios.map(mapRatio));
    setInsights(dashboard.ai_insights.map(mapInsight));
    setSources(dashboard.source_references.map(mapSource));
    setIssues(buildIssues(dashboard.extracted_metrics.metrics, dashboard.calculated_ratios.ratios));
  }

  const steps = buildProcessingSteps(workflowStatus);
  const downloadUrl =
    documentId && workflowStatus === "completed"
      ? dashboardViewMode === "compare" && comparison
        ? comparisonDownloadUrl(comparison.comparison_hash)
        : excelDownloadUrl(documentId)
      : undefined;

  return (
    <div className="min-h-screen bg-canvas text-ink">
      <div className="flex">
        <aside className="sticky top-0 hidden h-screen w-20 flex-col items-center border-r border-line bg-white px-3 py-5 lg:flex">
          <div className="grid h-11 w-11 place-items-center rounded-[8px] bg-ink text-white">
            <Building2 className="h-5 w-5" />
          </div>
          <nav className="mt-8 grid gap-3">
            {[BarChart3, Gauge, Search, Bell, Settings].map((Icon, index) => (
              <button
                key={index}
                type="button"
                className={`grid h-11 w-11 place-items-center rounded-[8px] transition ${
                  index === 0 ? "bg-mint text-white" : "text-muted hover:bg-canvas hover:text-ink"
                }`}
                aria-label={`Navigation item ${index + 1}`}
              >
                <Icon className="h-5 w-5" />
              </button>
            ))}
          </nav>
        </aside>

        <main className="min-w-0 flex-1">
          <header className="sticky top-0 z-10 border-b border-line bg-canvas/90 px-4 py-4 backdrop-blur md:px-6">
            <div className="mx-auto flex max-w-[1500px] items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  className="grid h-10 w-10 place-items-center rounded-[8px] border border-line bg-white text-ink lg:hidden"
                  aria-label="Open navigation"
                >
                  <Menu className="h-5 w-5" />
                </button>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.08em] text-muted">
                    CFO workspace
                  </p>
                  <h1 className="text-lg font-semibold text-ink md:text-xl">Financial Report Analyst</h1>
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <div className="hidden h-11 min-w-[280px] items-center gap-2 rounded-[8px] border border-line bg-white px-3 text-muted md:flex">
                  <Search className="h-4 w-4" />
                  <span className="text-sm">Search metrics, pages, insights</span>
                </div>
                {workflowStatus === "completed" && documentId !== null ? (
                  <div className="flex items-center gap-1 rounded-[8px] border border-line bg-white p-1 text-xs font-semibold">
                    <button
                      type="button"
                      onClick={() => setDashboardViewMode("single")}
                      className={`rounded-[6px] px-3 py-2 transition ${
                        dashboardViewMode === "single" ? "bg-mint text-white" : "text-muted hover:text-ink"
                      }`}
                    >
                      Single-year
                    </button>
                    <button
                      type="button"
                      disabled={!comparison}
                      onClick={() => setDashboardViewMode("compare")}
                      className={`rounded-[6px] px-3 py-2 transition disabled:cursor-not-allowed disabled:opacity-40 ${
                        dashboardViewMode === "compare" ? "bg-mint text-white" : "text-muted hover:text-ink"
                      }`}
                    >
                      Multi-year
                    </button>
                  </div>
                ) : null}
                <ExcelDownloadButton disabled={!downloadUrl} downloadUrl={downloadUrl} />
              </div>
            </div>
          </header>

          <div className="mx-auto grid max-w-[1500px] gap-6 px-4 py-6 md:px-6">
            <UploadPage
              onUpload={handleUpload}
              uploadedFile={uploadedFile}
              status={workflowStatus}
              errorMessage={errorMessage}
              trustSummary={trustSummary}
            />
            <ProcessingStatus
              steps={steps}
              uploadedFile={uploadedFile}
              status={workflowStatus}
              errorMessage={errorMessage}
            />
            {workflowStatus === "completed" && documentId !== null ? (
              <MultiYearSelector
                currentDocumentId={documentId}
                companyName={processedCompanyName}
                reportYear={processedReportYear}
                disabled={compareBusy}
                onCompare={handleCompare}
              />
            ) : null}

            {dashboardViewMode === "compare" && comparison ? (
              <MultiYearComparisonPanel data={comparison} />
            ) : (
              <>
                <FinancialSnapshotCards metrics={metrics} />
                <RatioAnalysisCards ratios={ratios} />
              </>
            )}

            <section className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
              <InsightPanel insights={insights} sourcesByPage={insightSnippetMap} />
              <IssuesPanel issues={issues} />
            </section>

            <CustomerFocusPanel sources={sources} issueCount={issues.length} />
          </div>
        </main>
      </div>
    </div>
  );
}

function buildProcessingSteps(status: UploadWorkflowStatus): ProcessingStep[] {
  const states = {
    upload: stepState(status, ["uploading", "processing", "completed", "failed"], "uploading"),
    parse: stepState(status, ["processing", "completed", "failed"], "processing"),
    extract: stepState(status, ["processing", "completed", "failed"], "processing"),
    analyze: stepState(status, ["completed"], "processing"),
  };

  return [
    { label: "Upload", status: states.upload, detail: "PDF sent to FastAPI" },
    { label: "Parse", status: states.parse, detail: "PyMuPDF and pdfplumber read pages" },
    { label: "Extract", status: states.extract, detail: "Gemini extracts metrics with sources" },
    { label: "Analyze", status: states.analyze, detail: "Python ratios, insights, and Excel export" },
  ];
}

function stepState(
  status: UploadWorkflowStatus,
  completeWhen: UploadWorkflowStatus[],
  activeWhen: UploadWorkflowStatus,
): "complete" | "active" | "queued" {
  if (status === activeWhen) return "active";
  if (completeWhen.includes(status)) return "complete";
  return "queued";
}

function mapMetric(metric: BackendMetric): FinancialMetric {
  const growth = growthRate(metric.current_year_value, metric.previous_year_value);
  return {
    metricName: labelize(metric.metric_name),
    currentYearValue: metric.current_year_value,
    previousYearValue: metric.previous_year_value,
    unit: metric.unit,
    sourcePage: metric.source_page,
    sourceText: metric.source_text ?? "",
    confidenceScore: metric.confidence_score,
    tone: metricTone(metric.metric_name, growth, metric.confidence_score),
  };
}

function mapRatio(ratio: BackendRatio): RatioMetric {
  const value = ratio.value;
  return {
    ratioName: labelize(ratio.ratio_name),
    value,
    unit: ratio.unit,
    explanation: ratio.explanation,
    tone: ratioTone(ratio.ratio_name, value),
  };
}

function mapInsight(insight: ProcessedDashboard["ai_insights"][number]): Insight {
  return {
    title: insight.title,
    type: insight.type,
    summary: insight.summary,
    supportingMetrics: insight.supporting_metrics.map(labelize),
    sourcePages: insight.source_pages,
    confidenceScore: insight.confidence_score,
  };
}

function mapSource(source: ProcessedDashboard["source_references"][number]): SourceReference {
  return {
    page: source.page,
    label: labelize(source.label),
    snippet: source.snippet,
    confidenceScore: source.confidence_score,
  };
}

function buildIssues(metrics: BackendMetric[], ratios: BackendRatio[]): Issue[] {
  const issues: Issue[] = [];
  metrics
    .filter((metric) => metric.confidence_score < 0.85)
    .forEach((metric) => {
      issues.push({
        title: `${labelize(metric.metric_name)} needs validation`,
        severity: "medium",
        description: `Extraction confidence is ${Math.round(metric.confidence_score * 100)}%.`,
        owner: "Data validation",
        sourcePage: metric.source_page ?? undefined,
      });
    });

  ratios
    .filter((ratio) => ratio.value === null)
    .slice(0, 4)
    .forEach((ratio) => {
      issues.push({
        title: `${labelize(ratio.ratio_name)} not calculated`,
        severity: "low",
        description: ratio.explanation,
        owner: "Finance review",
      });
    });

  return issues.length ? issues : [];
}

function buildTrustSummary(
  metrics: FinancialMetric[],
  sources: SourceReference[],
  issues: Issue[],
  status: UploadWorkflowStatus,
): TrustSummary {
  if (status !== "completed") {
    return {
      averageConfidence: null,
      sourcePageCount: null,
      openCheckCount: null,
    };
  }

  const confidenceValues = metrics.map((metric) => metric.confidenceScore);
  const averageConfidence = confidenceValues.length
    ? confidenceValues.reduce((total, value) => total + value, 0) / confidenceValues.length
    : null;

  return {
    averageConfidence,
    sourcePageCount: new Set(sources.map((source) => source.page)).size,
    openCheckCount: issues.length,
  };
}

function growthRate(current: number | null, previous: number | null) {
  if (current === null || previous === null || previous === 0) return null;
  return ((current - previous) / Math.abs(previous)) * 100;
}

function metricTone(metricName: string, growth: number | null, confidence: number): FinancialMetric["tone"] {
  if (confidence < 0.8) return "watch";
  if (growth === null) return "neutral";
  if (metricName === "operating_expenses") return growth > 15 ? "watch" : "neutral";
  return growth >= 0 ? "good" : "risk";
}

function ratioTone(ratioName: string, value: number | null): RatioMetric["tone"] {
  if (value === null) return "watch";
  if (ratioName.includes("cost_to_income")) return value > 50 ? "watch" : "good";
  if (ratioName.includes("growth")) return value >= 0 ? "good" : "risk";
  return value > 0 ? "good" : "neutral";
}

function labelize(value: string) {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
    .replace("Roe", "ROE")
    .replace("Roa", "ROA")
    .replace("Eps", "EPS");
}

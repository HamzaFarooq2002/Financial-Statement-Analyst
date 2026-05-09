import { AlertTriangle, CheckCircle2, Info, ShieldAlert } from "lucide-react";
import type { Insight, InsightType } from "../types";
import { formatConfidence } from "../utils/format";
import { SourceReference } from "./SourceReference";

interface InsightPanelProps {
  insights: Insight[];
  sourcesByPage?: Map<number, string>;
}

const insightIcons: Record<InsightType, typeof CheckCircle2> = {
  positive: CheckCircle2,
  warning: AlertTriangle,
  risk: ShieldAlert,
  neutral: Info,
};

const insightStyles: Record<InsightType, string> = {
  positive: "bg-mint/10 text-mint border-mint/30",
  warning: "bg-amber/10 text-amber border-amber/30",
  risk: "bg-coral/10 text-coral border-coral/30",
  neutral: "bg-aqua/10 text-aqua border-aqua/30",
};

export function InsightPanel({ insights, sourcesByPage }: InsightPanelProps) {
  return (
    <section className="rounded-[8px] border border-line bg-white p-5 shadow-soft">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-ink">CFO Insights</h2>
        <span className="rounded-full border border-line bg-canvas px-3 py-1.5 text-xs font-semibold text-muted">
          {insights.length} insights
        </span>
      </div>
      <div className="mt-5 grid gap-3">
        {!insights.length && (
          <div className="rounded-[8px] border border-line bg-canvas p-4 text-sm text-muted">
            CFO insights will appear after the backend finishes analysis.
          </div>
        )}
        {insights.map((insight) => {
          const Icon = insightIcons[insight.type];
          return (
            <article key={insight.title} className="rounded-[8px] border border-line bg-canvas p-4">
              <div className="flex items-start gap-3">
                <span className={`rounded-full border p-2 ${insightStyles[insight.type]}`}>
                  <Icon className="h-4 w-4" />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <h3 className="text-sm font-semibold text-ink">{insight.title}</h3>
                    <span className="text-xs font-semibold text-muted">
                      {formatConfidence(insight.confidenceScore)}
                    </span>
                  </div>
                  <p className="mt-2 text-sm leading-5 text-muted">{insight.summary}</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {insight.supportingMetrics.map((metric) => (
                      <span key={metric} className="rounded-full border border-line bg-white px-2.5 py-1 text-xs text-muted">
                        {metric}
                      </span>
                    ))}
                  </div>
                  {!!insight.sourcePages.length && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {insight.sourcePages.map((page) => (
                        <span
                          key={`${insight.title}-page-${page}`}
                          className="rounded-full border border-line bg-white px-2 py-1"
                        >
                          <SourceReference page={page} snippet={sourcesByPage?.get(page)} className="!text-xs" />
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

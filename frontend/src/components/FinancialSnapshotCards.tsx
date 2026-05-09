import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import type { FinancialMetric } from "../types";
import { formatConfidence, formatMoney, toneClass } from "../utils/format";
import { SourceReference } from "./SourceReference";

interface FinancialSnapshotCardsProps {
  metrics: FinancialMetric[];
}

export function FinancialSnapshotCards({ metrics }: FinancialSnapshotCardsProps) {
  return (
    <section>
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-ink">Financial Snapshot</h2>
        <span className="text-sm text-muted">Current vs previous year</span>
      </div>
      {!metrics.length && (
        <div className="rounded-[8px] border border-line bg-white p-5 text-sm text-muted shadow-soft">
          Upload and process a PDF to populate extracted financial metrics.
        </div>
      )}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {metrics.map((metric) => {
          const delta =
            metric.currentYearValue !== null && metric.previousYearValue
              ? ((metric.currentYearValue - metric.previousYearValue) / Math.abs(metric.previousYearValue)) * 100
              : null;
          const isPositive = delta !== null && delta >= 0;
          return (
            <article key={metric.metricName} className="rounded-[8px] border border-line bg-white p-5 shadow-soft">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold text-muted">{metric.metricName}</h3>
                  <p className="mt-3 text-2xl font-semibold text-ink">
                    {formatMoney(metric.currentYearValue, metric.unit)}
                  </p>
                </div>
                <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${toneClass(metric.tone)}`}>
                  {formatConfidence(metric.confidenceScore)}
                </span>
              </div>

              <div className="mt-5 flex items-center justify-between gap-3">
                <div className="text-sm text-muted">
                  <p>Previous</p>
                  <p className="mt-1 font-semibold text-ink">
                    {formatMoney(metric.previousYearValue, metric.unit)}
                  </p>
                </div>
                <div
                  className={`inline-flex items-center gap-1 rounded-full px-3 py-2 text-sm font-semibold ${
                    isPositive ? "bg-mint/10 text-mint" : "bg-coral/10 text-coral"
                  }`}
                >
                  {isPositive ? <ArrowUpRight className="h-4 w-4" /> : <ArrowDownRight className="h-4 w-4" />}
                  {delta === null ? "Missing" : `${delta.toFixed(1)}%`}
                </div>
              </div>

              <div className="mt-5 border-t border-line pt-4">
                <SourceReference page={metric.sourcePage} snippet={metric.sourceText} />
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

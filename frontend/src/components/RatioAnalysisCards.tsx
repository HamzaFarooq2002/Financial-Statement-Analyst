import { Activity, TrendingUp } from "lucide-react";
import type { RatioMetric } from "../types";
import { formatPercent, toneClass } from "../utils/format";

interface RatioAnalysisCardsProps {
  ratios: RatioMetric[];
}

export function RatioAnalysisCards({ ratios }: RatioAnalysisCardsProps) {
  return (
    <section>
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-ink">Ratio Analysis</h2>
        <TrendingUp className="h-5 w-5 text-mint" />
      </div>
      {!ratios.length && (
        <div className="rounded-[8px] border border-line bg-white p-5 text-sm text-muted shadow-soft">
          Ratios will appear after metric extraction completes.
        </div>
      )}
      <div className="grid gap-4 lg:grid-cols-4">
        {ratios.map((ratio) => (
          <article key={ratio.ratioName} className="rounded-[8px] border border-line bg-white p-5 shadow-soft">
            <div className="flex items-start justify-between gap-2">
              <div>
                <h3 className="text-sm font-semibold text-muted">{ratio.ratioName}</h3>
                <p className="mt-3 text-3xl font-semibold text-ink">{formatPercent(ratio.value)}</p>
              </div>
              <span className={`rounded-full border p-2 ${toneClass(ratio.tone)}`}>
                <Activity className="h-4 w-4" />
              </span>
            </div>
            <p className="mt-4 min-h-[60px] text-sm leading-5 text-muted">{ratio.explanation}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

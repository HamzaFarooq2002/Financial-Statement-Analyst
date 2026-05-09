import { BadgeCheck, Eye, Landmark, ListChecks } from "lucide-react";
import type { SourceReference } from "../types";
import { formatConfidence } from "../utils/format";

interface CustomerFocusPanelProps {
  sources: SourceReference[];
  issueCount: number;
}

export function CustomerFocusPanel({ sources, issueCount }: CustomerFocusPanelProps) {
  const uniqueSourcePages = new Set(sources.map((source) => source.page)).size;

  return (
    <section className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
      <div className="rounded-[8px] border border-line bg-white p-5 shadow-soft">
        <div className="flex items-center gap-3">
          <Landmark className="h-5 w-5 text-violet" />
          <h2 className="text-lg font-semibold text-ink">Decision Pack</h2>
        </div>
        <div className="mt-5 grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
          {[
            ["Board memo", sources.length ? "Ready" : "Pending"],
            ["Audit trail", sources.length ? `${sources.length} refs` : "Pending"],
            ["Source pages", uniqueSourcePages ? String(uniqueSourcePages) : "Pending"],
            ["Validation", sources.length ? `${issueCount} checks` : "Pending"],
          ].map(([label, value]) => (
            <div key={label} className="flex items-center justify-between rounded-[8px] border border-line bg-canvas p-4">
              <span className="text-sm text-muted">{label}</span>
              <span className="font-semibold text-ink">{value}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-[8px] border border-line bg-white p-5 shadow-soft">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Eye className="h-5 w-5 text-aqua" />
            <h2 className="text-lg font-semibold text-ink">Source Trace</h2>
          </div>
          <ListChecks className="h-5 w-5 text-mint" />
        </div>
        <div className="mt-5 grid gap-3">
          {!sources.length && (
            <div className="rounded-[8px] border border-line bg-canvas p-4 text-sm text-muted">
              Source references will appear once extracted metrics include page evidence.
            </div>
          )}
          {sources.map((source) => (
            <article key={`${source.page}-${source.label}`} className="rounded-[8px] border border-line bg-canvas p-4">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center gap-2">
                  <BadgeCheck className="h-4 w-4 text-mint" />
                  <h3 className="text-sm font-semibold text-ink">{source.label}</h3>
                </div>
                <span className="text-xs font-semibold text-muted">
                  Page {source.page} - {formatConfidence(source.confidenceScore)}
                </span>
              </div>
              <p className="mt-2 text-sm leading-5 text-muted">{source.snippet}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

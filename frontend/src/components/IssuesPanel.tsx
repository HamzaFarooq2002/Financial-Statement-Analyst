import { AlertCircle, ArrowRight } from "lucide-react";
import type { Issue } from "../types";

interface IssuesPanelProps {
  issues: Issue[];
}

const severityClass = {
  high: "bg-coral/10 text-coral border-coral/30",
  medium: "bg-amber/10 text-amber border-amber/30",
  low: "bg-aqua/10 text-aqua border-aqua/30",
};

export function IssuesPanel({ issues }: IssuesPanelProps) {
  return (
    <section className="rounded-[8px] border border-line bg-white p-5 shadow-soft">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-ink">Review Queue</h2>
        <AlertCircle className="h-5 w-5 text-amber" />
      </div>
      <div className="mt-5 grid gap-3">
        {!issues.length && (
          <div className="rounded-[8px] border border-line bg-canvas p-4 text-sm text-muted">
            Review items will appear when extraction confidence or ratio inputs need attention.
          </div>
        )}
        {issues.map((issue) => (
          <article key={issue.title} className="rounded-[8px] border border-line bg-canvas p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-ink">{issue.title}</h3>
                <p className="mt-2 text-sm leading-5 text-muted">{issue.description}</p>
              </div>
              <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${severityClass[issue.severity]}`}>
                {issue.severity}
              </span>
            </div>
            <div className="mt-4 flex items-center justify-between gap-3 border-t border-line pt-3 text-sm">
              <span className="text-muted">{issue.owner}</span>
              <span className="inline-flex items-center gap-1 font-semibold text-ink">
                Page {issue.sourcePage ?? "N/A"} <ArrowRight className="h-4 w-4" />
              </span>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

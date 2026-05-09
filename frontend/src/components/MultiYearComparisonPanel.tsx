import { FileSpreadsheet, TrendingUp } from "lucide-react";
import type { ComparisonResponse } from "../api/client";
import { comparisonDownloadUrl } from "../api/client";
import { formatConfidence } from "../utils/format";

type SeriesPoints = ComparisonResponse["metric_series"][number]["points"];

interface MultiYearComparisonPanelProps {
  data: ComparisonResponse;
}

function sortPoints<T extends { report_year: number | null; document_id: number }>(points: T[]): T[] {
  return [...points].sort((a, b) => {
    const ya = a.report_year ?? -1;
    const yb = b.report_year ?? -1;
    if (ya !== yb) return ya - yb;
    return a.document_id - b.document_id;
  });
}

function TrendSparkline({ points }: { points: SeriesPoints }) {
  const sortedPts = sortPoints(points).filter((p) => p.value !== null && p.value !== undefined);
  const vals = sortedPts.map((p) => p.value as number);
  if (vals.length < 2) {
    return <span className="text-xs text-muted">—</span>;
  }

  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const w = 72;
  const h = 28;
  const pad = 3;

  const coords = sortedPts.map((p, i) => {
    const x = pad + (sortedPts.length <= 1 ? w / 2 : (i / (sortedPts.length - 1)) * (w - pad * 2));
    const v = p.value as number;
    const yNorm = max === min ? 0.5 : (v - min) / (max - min);
    const y = pad + (1 - yNorm) * (h - pad * 2);
    return `${x},${y}`;
  });

  return (
    <svg width={w} height={h} className="shrink-0 text-mint" aria-hidden>
      <polyline
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={coords.join(" ")}
      />
    </svg>
  );
}

function formatCellValue(unit: string, value: number | null): string {
  if (value === null || value === undefined) return "—";
  if (unit === "%") return `${value.toFixed(2)}%`;
  if (Math.abs(value) >= 1e9) return `${(value / 1e9).toFixed(2)}B`;
  if (Math.abs(value) >= 1e6) return `${(value / 1e6).toFixed(2)}M`;
  if (Math.abs(value) >= 1e3) return `${(value / 1e3).toFixed(2)}K`;
  return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function YoYBudge({ pct }: { pct: number | null | undefined }) {
  if (pct === null || pct === undefined || Number.isNaN(pct)) {
    return <span className="text-xs text-muted">—</span>;
  }
  const positive = pct >= 0;
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
        positive ? "bg-mint/15 text-mint" : "bg-coral/15 text-coral"
      }`}
    >
      {positive ? "+" : ""}
      {pct.toFixed(1)}%
    </span>
  );
}

export function MultiYearComparisonPanel({ data }: MultiYearComparisonPanelProps) {
  const docCols = [...data.documents].sort((a, b) => {
    const ya = a.report_year ?? -1;
    const yb = b.report_year ?? -1;
    if (ya !== yb) return ya - yb;
    return a.document_id - b.document_id;
  });

  const excelUrl = comparisonDownloadUrl(data.comparison_hash);

  return (
    <div className="grid gap-6">
      <section className="rounded-[8px] border border-line bg-white p-5 shadow-soft">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-mint" />
            <h2 className="text-lg font-semibold text-ink">Multi-year trend summary</h2>
          </div>
          <a
            href={excelUrl}
            className="inline-flex h-10 items-center gap-2 rounded-[8px] border border-line bg-canvas px-3 text-sm font-semibold text-ink transition hover:border-mint hover:text-mint"
          >
            <FileSpreadsheet className="h-4 w-4" />
            Download comparison Excel
          </a>
        </div>
        <p className="mt-3 text-base font-semibold text-ink">{data.trend_summary.headline}</p>
        <p className="mt-1 text-xs text-muted">Model confidence: {formatConfidence(data.trend_summary.confidence)}</p>
        <ul className="mt-4 list-inside list-disc space-y-2 text-sm leading-6 text-muted">
          {data.trend_summary.bullets.map((b, i) => (
            <li key={i}>{b}</li>
          ))}
        </ul>
      </section>

      <ComparisonTable
        title="Metric trends"
        columns={docCols}
        series={data.metric_series.map((s) => ({
          name: s.metric_name,
          unit: s.unit,
          points: s.points,
        }))}
      />

      <ComparisonTable
        title="Ratio trends"
        columns={docCols}
        series={data.ratio_series.map((s) => ({
          name: s.ratio_name,
          unit: s.unit,
          points: s.points,
        }))}
      />
    </div>
  );
}

function ComparisonTable({
  title,
  columns,
  series,
}: {
  title: string;
  columns: ComparisonResponse["documents"];
  series: { name: string; unit: string; points: SeriesPoints }[];
}) {
  return (
    <section className="rounded-[8px] border border-line bg-white shadow-soft">
      <div className="border-b border-line px-5 py-4">
        <h2 className="text-lg font-semibold text-ink">{title}</h2>
      </div>
      <div className="overflow-x-auto px-2 py-2 md:px-4 md:py-4">
        <table className="min-w-full border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-line text-xs font-semibold uppercase tracking-wide text-muted">
              <th className="sticky left-0 z-[1] bg-white px-3 py-2">Name</th>
              <th className="px-3 py-2">Unit</th>
              {columns.map((c) => (
                <th key={c.document_id} className="whitespace-nowrap px-3 py-2">
                  {c.report_year ?? "—"}
                  <span className="block font-normal normal-case text-muted">#{c.document_id}</span>
                </th>
              ))}
              <th className="px-3 py-2">YoY %</th>
              <th className="px-3 py-2">Trend</th>
            </tr>
          </thead>
          <tbody>
            {series.map((row) => {
              const sortedPts = sortPoints(row.points);
              const last = sortedPts[sortedPts.length - 1];
              const yoy = last?.yoy_percent;

              return (
                <tr key={row.name} className="border-b border-line/80">
                  <td className="sticky left-0 z-[1] bg-white px-3 py-3 font-semibold text-ink">{row.name}</td>
                  <td className="px-3 py-3 text-muted">{row.unit}</td>
                  {columns.map((c) => {
                    const p = row.points.find((pt) => pt.document_id === c.document_id);
                    return (
                      <td key={c.document_id} className="whitespace-nowrap px-3 py-3 tabular-nums text-ink">
                        {formatCellValue(row.unit, p?.value ?? null)}
                      </td>
                    );
                  })}
                  <td className="px-3 py-3">
                    <YoYBudge pct={yoy} />
                  </td>
                  <td className="px-3 py-3">
                    <TrendSparkline points={row.points} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

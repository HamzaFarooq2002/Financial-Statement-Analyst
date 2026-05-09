import { useEffect, useState } from "react";
import { BarChart3, Loader2 } from "lucide-react";
import { getRelatedDocuments, type DocumentSummary } from "../api/client";

interface MultiYearSelectorProps {
  currentDocumentId: number | null;
  companyName?: string | null;
  reportYear?: number | null;
  disabled?: boolean;
  onCompare: (documentIds: number[]) => void;
}

export function MultiYearSelector({
  currentDocumentId,
  companyName,
  reportYear,
  disabled = false,
  onCompare,
}: MultiYearSelectorProps) {
  const [related, setRelated] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | undefined>();
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  useEffect(() => {
    setSelectedIds(new Set());
    setRelated([]);
    setFetchError(undefined);

    if (currentDocumentId == null) return;

    let cancelled = false;
    setLoading(true);
    getRelatedDocuments(currentDocumentId)
      .then((docs) => {
        if (!cancelled) setRelated(docs);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setFetchError(err instanceof Error ? err.message : "Could not load related reports.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [currentDocumentId]);

  function toggle(id: number) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function handleCompare() {
    if (currentDocumentId == null) return;
    const ids = [currentDocumentId, ...Array.from(selectedIds)].sort((a, b) => a - b);
    if (ids.length < 2) return;
    onCompare(ids);
  }

  if (currentDocumentId == null) return null;

  const label =
    companyName && reportYear != null
      ? `${companyName} (${reportYear})`
      : companyName || `Document #${currentDocumentId}`;

  return (
    <section className="rounded-[8px] border border-line bg-white p-5 shadow-soft">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-[8px] bg-mint/15 text-mint">
            <BarChart3 className="h-5 w-5" />
          </span>
          <div>
            <h2 className="text-lg font-semibold text-ink">Compare multiple years</h2>
            <p className="mt-1 text-sm text-muted">
              Current report: <span className="font-semibold text-ink">{label}</span>. Select other processed reports for
              the same company to build trend tables and a comparison Excel.
            </p>
          </div>
        </div>
      </div>

      <div className="mt-4 border-t border-line pt-4">
        {loading ? (
          <div className="flex items-center gap-2 text-sm text-muted">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading related reports…
          </div>
        ) : fetchError ? (
          <p className="text-sm text-coral">{fetchError}</p>
        ) : related.length === 0 ? (
          <p className="text-sm italic text-muted">
            No other completed reports found for this company yet. Process another PDF with the same{" "}
            <span className="font-semibold not-italic text-ink">company_name</span> to enable comparison.
          </p>
        ) : (
          <ul className="grid gap-2 sm:grid-cols-2">
            {related.map((doc) => (
              <li key={doc.document_id}>
                <label className="flex cursor-pointer items-start gap-3 rounded-[8px] border border-line bg-canvas px-3 py-2 transition hover:border-mint/40">
                  <input
                    type="checkbox"
                    className="mt-1 h-4 w-4 rounded border-line text-mint focus:ring-mint"
                    checked={selectedIds.has(doc.document_id)}
                    onChange={() => toggle(doc.document_id)}
                    disabled={disabled}
                  />
                  <span className="min-w-0 text-sm">
                    <span className="font-semibold text-ink">{doc.file_name}</span>
                    <span className="mt-0.5 block text-xs text-muted">
                      {doc.company_name ?? "—"}
                      {doc.report_year != null ? ` · ${doc.report_year}` : ""}
                    </span>
                  </span>
                </label>
              </li>
            ))}
          </ul>
        )}

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            type="button"
            disabled={
              disabled ||
              loading ||
              currentDocumentId == null ||
              selectedIds.size === 0 ||
              related.length === 0
            }
            onClick={handleCompare}
            className="inline-flex h-10 items-center justify-center rounded-[8px] bg-ink px-4 text-sm font-semibold text-white transition hover:bg-aqua focus:outline-none focus:ring-2 focus:ring-mint focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-line disabled:text-muted"
          >
            Run comparison ({1 + selectedIds.size} reports)
          </button>
        </div>
      </div>
    </section>
  );
}

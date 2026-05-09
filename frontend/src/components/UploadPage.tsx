import { FileText, ShieldCheck, Sparkles, UploadCloud } from "lucide-react";
import { useRef, useState } from "react";
import type { TrustSummary } from "../types";
import { formatConfidence, formatInteger } from "../utils/format";

interface UploadPageProps {
  onUpload: (file: File) => void;
  uploadedFile: string;
  status: "idle" | "uploading" | "processing" | "completed" | "failed";
  errorMessage?: string;
  trustSummary: TrustSummary;
}

export function UploadPage({ onUpload, uploadedFile, status, errorMessage, trustSummary }: UploadPageProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  function handleFile(file?: File) {
    if (!file) return;
    onUpload(file);
  }

  const isBusy = status === "uploading" || status === "processing";

  return (
    <section className="grid gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.65fr)]">
      <div
        className={`min-h-[260px] rounded-[8px] border-2 border-dashed bg-white p-6 shadow-soft transition ${
          isDragging ? "border-mint bg-mint/5" : "border-line"
        }`}
        onDragEnter={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setIsDragging(false);
          handleFile(event.dataTransfer.files[0]);
        }}
      >
        <div className="flex h-full flex-col justify-between gap-8">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.08em] text-mint">
                Annual report intake
              </p>
              <h1 className="mt-3 max-w-3xl text-3xl font-semibold text-ink md:text-5xl">
                AI Financial Report Analyst
              </h1>
              <p className="mt-4 max-w-2xl text-sm leading-6 text-muted md:text-base">
                Upload the PDF, review extracted financials, inspect ratios, validate source pages,
                and export the workbook.
              </p>
            </div>
            <div className="hidden h-14 w-14 place-items-center rounded-[8px] bg-ink text-white md:grid">
              <Sparkles className="h-6 w-6" />
            </div>
          </div>

          <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
            <input
              ref={inputRef}
              type="file"
              accept="application/pdf"
              className="hidden"
              onChange={(event) => handleFile(event.target.files?.[0])}
            />
            <button
              type="button"
              disabled={isBusy}
              onClick={() => inputRef.current?.click()}
              className="inline-flex h-12 items-center justify-center gap-2 rounded-[8px] bg-ink px-5 text-sm font-semibold text-white transition hover:bg-mint focus:outline-none focus:ring-2 focus:ring-mint focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-line disabled:text-muted"
            >
              <UploadCloud className="h-5 w-5" />
              {isBusy ? "Processing..." : "Upload PDF"}
            </button>
            <div className="flex flex-wrap gap-2 text-xs font-medium text-muted">
              <span className="rounded-full border border-line bg-canvas px-3 py-2">PDF only</span>
              <span className="rounded-full border border-line bg-canvas px-3 py-2">Source traced</span>
              <span className="rounded-full border border-line bg-canvas px-3 py-2">Excel ready</span>
            </div>
          </div>
          {errorMessage && (
            <div className="rounded-[8px] border border-coral/30 bg-coral/10 px-4 py-3 text-sm font-medium text-coral">
              {errorMessage}
            </div>
          )}
        </div>
      </div>

      <aside className="grid gap-3">
        <div className="rounded-[8px] border border-line bg-white p-5 shadow-soft">
          <div className="flex items-center gap-3">
            <FileText className="h-5 w-5 text-aqua" />
            <h2 className="text-sm font-semibold text-ink">Current file</h2>
          </div>
          <p className="mt-4 text-lg font-semibold text-ink">{uploadedFile}</p>
          <p className="mt-2 text-sm text-muted">PDF analysis workspace</p>
        </div>
        <div className="rounded-[8px] border border-line bg-white p-5 shadow-soft">
          <div className="flex items-center gap-3">
            <ShieldCheck className="h-5 w-5 text-mint" />
            <h2 className="text-sm font-semibold text-ink">Trust layer</h2>
          </div>
          <div className="mt-4 grid grid-cols-3 gap-2 text-center">
            <div>
              <p className="text-xl font-semibold text-ink">
                {trustSummary.averageConfidence === null
                  ? "Pending"
                  : formatConfidence(trustSummary.averageConfidence)}
              </p>
              <p className="mt-1 text-xs text-muted">Avg confidence</p>
            </div>
            <div>
              <p className="text-xl font-semibold text-ink">
                {formatInteger(trustSummary.sourcePageCount)}
              </p>
              <p className="mt-1 text-xs text-muted">Source pages</p>
            </div>
            <div>
              <p className="text-xl font-semibold text-ink">
                {formatInteger(trustSummary.openCheckCount)}
              </p>
              <p className="mt-1 text-xs text-muted">Open checks</p>
            </div>
          </div>
        </div>
      </aside>
    </section>
  );
}

import { FileSearch } from "lucide-react";

interface SourceReferenceProps {
  page?: number | null;
  snippet?: string | null;
  className?: string;
}

export function SourceReference({ page, snippet, className = "" }: SourceReferenceProps) {
  if (page === null || page === undefined) {
    return (
      <div className={`inline-flex flex-wrap items-center gap-1.5 text-xs text-muted ${className}`}>
        <FileSearch className="h-3.5 w-3.5 shrink-0 text-aqua" />
        <span>Page N/A</span>
      </div>
    );
  }

  return (
    <div
      className={`inline-flex max-w-full flex-wrap items-center gap-1.5 text-xs text-muted ${className}`}
      title={snippet ? snippet : undefined}
    >
      <FileSearch className="h-3.5 w-3.5 shrink-0 text-aqua" />
      <span className="font-semibold text-ink">Page {page}</span>
      {snippet ? (
        <span className="truncate text-muted">• “{snippet.length > 100 ? `${snippet.slice(0, 100)}…` : snippet}”</span>
      ) : null}
    </div>
  );
}

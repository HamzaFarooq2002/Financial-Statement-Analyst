import { Download, FileSpreadsheet } from "lucide-react";

interface ExcelDownloadButtonProps {
  disabled?: boolean;
  downloadUrl?: string;
}

export function ExcelDownloadButton({ disabled = false, downloadUrl }: ExcelDownloadButtonProps) {
  function handleDownload() {
    if (!downloadUrl) return;
    window.location.href = downloadUrl;
  }

  return (
    <button
      type="button"
      disabled={disabled}
      onClick={handleDownload}
      className="inline-flex h-11 items-center justify-center gap-2 rounded-[8px] bg-mint px-4 text-sm font-semibold text-white transition hover:bg-aqua focus:outline-none focus:ring-2 focus:ring-mint focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-line disabled:text-muted"
    >
      <FileSpreadsheet className="h-5 w-5" />
      Export Excel
      <Download className="h-4 w-4" />
    </button>
  );
}

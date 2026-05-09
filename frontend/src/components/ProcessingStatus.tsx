import { CheckCircle2, Clock3, Loader2 } from "lucide-react";
import type { ProcessingStep, UploadWorkflowStatus } from "../types";

interface ProcessingStatusProps {
  steps: ProcessingStep[];
  uploadedFile: string;
  status: UploadWorkflowStatus;
  errorMessage?: string;
}

export function ProcessingStatus({ steps, uploadedFile, status, errorMessage }: ProcessingStatusProps) {
  const badge = statusBadge(status);

  return (
    <section className="rounded-[8px] border border-line bg-white p-5 shadow-soft">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-ink">Processing Status</h2>
          <p className="mt-1 text-sm text-muted">{uploadedFile}</p>
        </div>
        <span className={`inline-flex w-fit items-center gap-2 rounded-full border px-3 py-2 text-xs font-semibold ${badge.className}`}>
          {badge.spinning ? <Loader2 className="h-4 w-4 animate-spin" /> : badge.icon}
          {badge.label}
        </span>
      </div>
      {errorMessage && (
        <p className="mt-4 rounded-[8px] border border-coral/30 bg-coral/10 px-4 py-3 text-sm font-medium text-coral">
          {errorMessage}
        </p>
      )}

      <div className="mt-5 grid gap-3 md:grid-cols-4">
        {steps.map((step) => (
          <div key={step.label} className="rounded-[8px] border border-line bg-canvas p-4">
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-sm font-semibold text-ink">{step.label}</h3>
              {step.status === "complete" && <CheckCircle2 className="h-5 w-5 text-mint" />}
              {step.status === "active" && <Loader2 className="h-5 w-5 animate-spin text-amber" />}
              {step.status === "queued" && <Clock3 className="h-5 w-5 text-muted" />}
            </div>
            <p className="mt-3 min-h-[40px] text-sm leading-5 text-muted">{step.detail}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function statusBadge(status: UploadWorkflowStatus) {
  if (status === "completed") {
    return {
      label: "Completed",
      className: "border-mint/30 bg-mint/10 text-mint",
      icon: <CheckCircle2 className="h-4 w-4" />,
      spinning: false,
    };
  }
  if (status === "failed") {
    return {
      label: "Failed",
      className: "border-coral/30 bg-coral/10 text-coral",
      icon: <Clock3 className="h-4 w-4" />,
      spinning: false,
    };
  }
  if (status === "processing" || status === "uploading") {
    return {
      label: status === "uploading" ? "Uploading" : "Processing",
      className: "border-amber/30 bg-amber/10 text-amber",
      icon: null,
      spinning: true,
    };
  }
  return {
    label: "Waiting",
    className: "border-line bg-canvas text-muted",
    icon: <Clock3 className="h-4 w-4" />,
    spinning: false,
  };
}

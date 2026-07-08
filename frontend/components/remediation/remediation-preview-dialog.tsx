"use client"

import { AlertTriangle, PlayCircle, ShieldAlert } from "lucide-react"

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { CleaningPreviewTable } from "@/components/remediation/cleaning-preview-table"
import { RiskBadge } from "@/components/remediation/risk-badge"
import type { CleaningPreview, CleaningSuggestion } from "@/lib/types"

type RemediationPreviewDialogProps = {
  open: boolean
  mode: "create" | "execute"
  preview?: CleaningPreview | null
  suggestion?: CleaningSuggestion
  saving?: boolean
  error?: string
  onOpenChange: (open: boolean) => void
  onConfirm: () => void
}

export function RemediationPreviewDialog({
  open,
  mode,
  preview,
  suggestion,
  saving = false,
  error,
  onOpenChange,
  onConfirm,
}: RemediationPreviewDialogProps) {
  const title = mode === "execute" ? "Create and Execute Cleaning Job" : "Create Cleaning Job"
  const description =
    mode === "execute"
      ? "Review the dry-run preview before creating, approving, and executing this job."
      : "Review the dry-run preview before submitting this remediation job."

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl p-0 sm:max-w-3xl">
        <DialogHeader className="border-b p-5">
          <div className="flex items-start gap-3">
            <div className="flex size-10 items-center justify-center rounded-xl border border-blue-100 bg-blue-50 text-blue-700">
              {mode === "execute" ? <PlayCircle className="size-5" /> : <ShieldAlert className="size-5" />}
            </div>
            <div>
              <DialogTitle>{title}</DialogTitle>
              <DialogDescription className="mt-1">{description}</DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="grid gap-5 p-5">
          <div className="rounded-xl border bg-slate-50 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-sm font-semibold text-slate-950">{preview?.summary ?? "No preview available"}</div>
                <div className="mt-1 text-sm text-slate-500">
                  {preview?.target_table}.{preview?.target_column ?? "column"} · {preview?.total_rows_targeted ?? 0} row(s)
                </div>
              </div>
              {suggestion ? <RiskBadge risk={suggestion.risk} /> : null}
            </div>
          </div>

          {preview?.preview_rows?.length ? (
            <CleaningPreviewTable rows={preview.preview_rows} />
          ) : (
            <div className="rounded-xl border border-amber-100 bg-amber-50 p-4 text-sm text-amber-800">
              No row-level preview rows were returned. Review the target carefully before continuing.
            </div>
          )}

          {error ? (
            <div className="flex items-start gap-2 rounded-xl border border-red-100 bg-red-50 p-3 text-sm text-red-700">
              <AlertTriangle className="mt-0.5 size-4 shrink-0" />
              <span>{error}</span>
            </div>
          ) : null}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={onConfirm} disabled={saving || !preview}>
            {saving ? "Working..." : mode === "execute" ? "Create and Execute" : "Create Job"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

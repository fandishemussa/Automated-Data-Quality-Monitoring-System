"use client"

import { AlertTriangle, CheckCircle2, RotateCcw, ShieldCheck, Wrench } from "lucide-react"

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { JobStatusBadge } from "@/components/remediation/job-status-badge"
import { StatusBadge } from "@/components/ui-custom/status-badge"
import { formatDateTime } from "@/lib/formatters"
import type { CleaningJob, ProposedCleaningChange } from "@/lib/types"

export type RemediationAction = "approve" | "execute" | "rollback"

type RemediationActionDialogProps = {
  job?: CleaningJob
  action?: RemediationAction
  open: boolean
  saving?: boolean
  error?: string
  onOpenChange: (open: boolean) => void
  onConfirm: () => void
}

const actionCopy: Record<RemediationAction, { title: string; description: string; confirm: string; tone: string }> = {
  approve: {
    title: "Approve Cleaning Job",
    description: "Review the proposed before/after values before releasing this job for execution.",
    confirm: "Approve Job",
    tone: "border-green-100 bg-green-50 text-green-700",
  },
  execute: {
    title: "Execute Cleaning Job",
    description: "This will apply the approved remediation action to the configured source table.",
    confirm: "Execute Job",
    tone: "border-blue-100 bg-blue-50 text-blue-700",
  },
  rollback: {
    title: "Rollback Cleaning Job",
    description: "This will restore values using the recorded change history for this executed job.",
    confirm: "Rollback Job",
    tone: "border-amber-100 bg-amber-50 text-amber-700",
  },
}

export function RemediationActionDialog({
  job,
  action = "approve",
  open,
  saving = false,
  error,
  onOpenChange,
  onConfirm,
}: RemediationActionDialogProps) {
  const copy = actionCopy[action]
  const proposed = job?.proposed_changes ?? []
  const changes = job?.change_log ?? []
  const rowsToShow = action === "rollback" ? changes : proposed
  const Icon = action === "rollback" ? RotateCcw : action === "execute" ? Wrench : ShieldCheck

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl p-0 sm:max-w-3xl">
        <DialogHeader className="border-b p-5">
          <div className="flex items-start gap-3">
            <div className={`flex size-10 items-center justify-center rounded-xl border ${copy.tone}`}>
              <Icon className="size-5" />
            </div>
            <div>
              <DialogTitle>{copy.title}</DialogTitle>
              <DialogDescription className="mt-1">{copy.description}</DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="grid gap-5 p-5">
          {job ? (
            <div className="rounded-xl border bg-slate-50 p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="text-sm font-semibold text-slate-950">Cleaning Job #{job.id}</div>
                  <div className="mt-1 text-xs uppercase tracking-wide text-slate-500">
                    {job.dataset_name ?? "Dataset"} / {job.cleaning_action ?? "Cleaning action"}
                  </div>
                </div>
                <JobStatusBadge status={job.status} />
              </div>
              <div className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
                <InfoTile label="Target" value={`${job.target_table ?? "table"}.${job.target_column ?? "column"}`} />
                <InfoTile label="Requested By" value={job.requested_by || "Unknown"} />
                <InfoTile label="Created" value={formatDateTime(job.created_at)} />
              </div>
            </div>
          ) : null}

          <div>
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="text-sm font-semibold">
                  {action === "rollback" ? "Recorded Change History" : "Proposed Before/After Changes"}
                </div>
                <div className="text-sm text-slate-500">
                  {action === "rollback"
                    ? "Rollback uses these recorded old values."
                    : "Admins should confirm these values before approval or execution."}
                </div>
              </div>
              <StatusBadge status={`${rowsToShow.length} row(s)`} />
            </div>
            {!rowsToShow.length ? (
              <div className="rounded-xl border border-amber-100 bg-amber-50 p-4 text-sm text-amber-800">
                No row-level change preview is recorded for this job. Review the target table, column, and action carefully.
              </div>
            ) : (
              <div className="max-h-80 space-y-2 overflow-y-auto rounded-xl border bg-white p-3">
                {rowsToShow.map((change, index) => (
                  <ChangeRow key={`${change.row_identifier}-${index}`} change={change} />
                ))}
              </div>
            )}
          </div>

          {action === "execute" ? (
            <div className="flex items-start gap-2 rounded-xl border border-blue-100 bg-blue-50 p-3 text-sm text-blue-700">
              <CheckCircle2 className="mt-0.5 size-4 shrink-0" />
              Execution writes source changes and records before/after values in change history.
            </div>
          ) : null}

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
          <Button onClick={onConfirm} disabled={saving || !job}>
            {saving ? "Working..." : copy.confirm}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function InfoTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-white p-3">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 truncate font-medium text-slate-900" title={value}>
        {value}
      </div>
    </div>
  )
}

function ChangeRow({ change }: { change: ProposedCleaningChange }) {
  return (
    <div className="rounded-lg border bg-slate-50 p-3 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="font-medium text-slate-700">
          {change.table_name}.{change.column_name}
        </div>
        <div className="text-xs text-slate-500">{change.row_identifier}</div>
      </div>
      <div className="mt-2 grid gap-2 sm:grid-cols-[1fr_auto_1fr]">
        <span className="truncate rounded-md bg-white px-2 py-1 text-slate-600" title={String(change.old_value ?? "")}>
          {String(change.old_value ?? "NULL")}
        </span>
        <span className="self-center text-center text-slate-400">to</span>
        <span className="truncate rounded-md bg-white px-2 py-1 font-medium text-slate-950" title={String(change.new_value ?? "")}>
          {String(change.new_value ?? "NULL")}
        </span>
      </div>
    </div>
  )
}

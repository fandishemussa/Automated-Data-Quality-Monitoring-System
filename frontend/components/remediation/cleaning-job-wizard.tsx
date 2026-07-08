"use client"

import { useEffect, useState } from "react"

import { CleaningActionCard } from "@/components/remediation/cleaning-action-card"
import { CleaningPreviewTable } from "@/components/remediation/cleaning-preview-table"
import { RemediationPreviewDialog } from "@/components/remediation/remediation-preview-dialog"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { RiskBadge } from "@/components/remediation/risk-badge"
import { api, getStoredUserRole } from "@/lib/api-client"
import type { CleanableIssue, CleaningPayload, CleaningPreview, CleaningSuggestion } from "@/lib/types"

type CleaningJobWizardProps = {
  issue?: CleanableIssue
  suggestions: CleaningSuggestion[]
  onJobCreated: () => void
}

export function CleaningJobWizard({ issue, suggestions, onJobCreated }: CleaningJobWizardProps) {
  const [selected, setSelected] = useState<CleaningSuggestion | undefined>()
  const [targetTable, setTargetTable] = useState(issue?.dataset_name ?? "")
  const [targetColumn, setTargetColumn] = useState(issue?.column_name ?? "")
  const [rowIdentifier, setRowIdentifier] = useState(issue?.row_identifier ?? "")
  const [newValue, setNewValue] = useState("")
  const [pattern, setPattern] = useState("")
  const [replacement, setReplacement] = useState("")
  const [preview, setPreview] = useState<CleaningPreview | null>(null)
  const [reviewMode, setReviewMode] = useState<"create" | "execute">("create")
  const [reviewOpen, setReviewOpen] = useState(false)
  const [reviewSaving, setReviewSaving] = useState(false)
  const [reviewError, setReviewError] = useState("")
  const [message, setMessage] = useState("")

  useEffect(() => {
    setSelected(suggestions[0])
    setTargetTable(issue?.dataset_name ?? "")
    setTargetColumn(issue?.column_name ?? "")
    setRowIdentifier(issue?.row_identifier ?? "")
    setNewValue("")
    setPattern("")
    setReplacement("")
    setPreview(null)
    setMessage(issue ? "Select an action, configure values if needed, then preview." : "")
  }, [issue, suggestions])

  if (!issue) {
    return (
      <Card className="rounded-xl shadow-sm">
        <CardHeader>
          <CardTitle>Cleaning Job Wizard</CardTitle>
          <CardDescription>Select an issue first to create a cleaning job.</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  function buildPayload(): CleaningPayload {
    return {
      issue_id: Number(issue?.id),
      action: selected?.action ?? "",
      target_table: targetTable,
      target_column: targetColumn,
      row_identifier: rowIdentifier,
      new_value: newValue,
      parameters: { pattern, replacement, min: newValue, max: newValue },
    }
  }

  async function runPreview() {
    if (!selected) {
      setMessage("Select a cleaning action first.")
      return
    }
    try {
      const result = await api.previewCleaning(buildPayload())
      setPreview(result)
      setMessage("Preview generated. Review before creating a job.")
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Preview failed.")
    }
  }

  async function performCreateJob() {
    if (!preview) {
      setMessage("Preview is required before creating a job.")
      return undefined
    }
    try {
      const job = await api.createCleaningJob(buildPayload())
      setMessage(`Cleaning job #${job.id} created with status ${job.status}.`)
      onJobCreated()
      return job
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not create cleaning job.")
      return undefined
    }
  }

  function requestCreateJob() {
    if (!preview) {
      setMessage("Preview is required before creating a job.")
      return
    }
    setReviewMode("create")
    setReviewError("")
    setReviewOpen(true)
  }

  async function confirmCreateJob() {
    setReviewSaving(true)
    setReviewError("")
    try {
      const job = await performCreateJob()
      if (job) {
        setReviewOpen(false)
      }
    } catch (err) {
      setReviewError(err instanceof Error ? err.message : "Could not create cleaning job.")
    } finally {
      setReviewSaving(false)
    }
  }

  const canExecute = getStoredUserRole() === "admin"

  function requestExecuteNow() {
    if (!preview) {
      setMessage("Preview is required before execution.")
      return
    }
    if (!canExecute) {
      setMessage("Only admin users can execute immediately.")
      return
    }
    setReviewMode("execute")
    setReviewError("")
    setReviewOpen(true)
  }

  async function confirmExecuteNow() {
    setReviewSaving(true)
    setReviewError("")
    const job = await performCreateJob()
    if (!job) {
      setReviewSaving(false)
      return
    }

    try {
      let executableJob = job
      if (job.status === "PENDING_APPROVAL") {
        executableJob = await api.approveCleaningJob(job.id)
      }
      if (executableJob.status !== "APPROVED" && executableJob.status !== "READY_FOR_EXECUTION") {
        setMessage(`Job #${job.id} was created but is not executable yet. Current status: ${executableJob.status}.`)
        return
      }
      const executed = await api.executeCleaningJob(job.id)
      setMessage(`Cleaning job #${executed.id} executed. ${executed.total_rows_updated ?? 0} row(s) updated.`)
      setReviewOpen(false)
      onJobCreated()
    } catch (err) {
      setReviewError(err instanceof Error ? err.message : "Execute Now failed.")
    } finally {
      setReviewSaving(false)
    }
  }

  async function confirmReviewAction() {
    if (reviewMode === "create") {
      await confirmCreateJob()
    } else {
      await confirmExecuteNow()
    }
  }

  return (
    <Card className="rounded-xl shadow-sm">
      <CardHeader>
        <CardTitle>Cleaning Job Wizard</CardTitle>
        <CardDescription>Preview first, then submit for approval or execution.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <section>
          <div className="text-sm font-semibold">Step 1: Selected issue</div>
          <div className="mt-2 rounded-xl border bg-slate-50 p-3 text-sm">
            #{issue.id} {issue.dataset_name}.{issue.column_name} - {issue.reason}
          </div>
        </section>
        <section>
          <div className="text-sm font-semibold">Step 2: Select cleaning action</div>
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            {suggestions.map((suggestion) => (
              <CleaningActionCard
                key={suggestion.action}
                suggestion={suggestion}
                selected={selected?.action === suggestion.action}
                onSelect={(next) => {
                  setSelected(next)
                  setPreview(null)
                }}
              />
            ))}
          </div>
        </section>
        <section className="grid gap-3 md:grid-cols-2">
          <div>
            <label className="text-sm font-medium">Target table</label>
            <Input value={targetTable} onChange={(event) => setTargetTable(event.target.value)} />
          </div>
          <div>
            <label className="text-sm font-medium">Target column</label>
            <Input value={targetColumn} onChange={(event) => setTargetColumn(event.target.value)} />
          </div>
          <div>
            <label className="text-sm font-medium">Row identifier</label>
            <Input value={rowIdentifier} onChange={(event) => setRowIdentifier(event.target.value)} placeholder="id=123" />
          </div>
          <div>
            <label className="text-sm font-medium">New value</label>
            <Input value={newValue} onChange={(event) => setNewValue(event.target.value)} placeholder="Replacement value" />
          </div>
          {selected?.action === "regex_replace" ? (
            <>
              <Input value={pattern} onChange={(event) => setPattern(event.target.value)} placeholder="Regex pattern" />
              <Input value={replacement} onChange={(event) => setReplacement(event.target.value)} placeholder="Replacement" />
            </>
          ) : null}
        </section>
        <section className="flex items-center justify-between rounded-xl border bg-slate-50 p-3">
          <div>
            <div className="text-sm font-semibold">Step 4: Preview changes</div>
            <p className="text-sm text-slate-500">Always dry-run before creating a job.</p>
          </div>
          {selected ? <RiskBadge risk={selected.risk} /> : null}
        </section>
        <div className="flex flex-wrap gap-2">
          <Button onClick={runPreview}>Preview</Button>
          <Button onClick={requestCreateJob} disabled={!preview}>Create Job</Button>
          <Button variant="outline" onClick={requestExecuteNow} disabled={!canExecute || !preview}>Execute Now</Button>
        </div>
        {message ? <div className="rounded-xl border bg-blue-50 p-3 text-sm text-blue-700">{message}</div> : null}
        {preview ? (
          <div className="space-y-3">
            <div className="text-sm text-slate-600">{preview.summary}</div>
            <CleaningPreviewTable rows={preview.preview_rows} />
          </div>
        ) : null}
      </CardContent>
      <RemediationPreviewDialog
        open={reviewOpen}
        mode={reviewMode}
        preview={preview}
        suggestion={selected}
        saving={reviewSaving}
        error={reviewError}
        onOpenChange={setReviewOpen}
        onConfirm={confirmReviewAction}
      />
    </Card>
  )
}

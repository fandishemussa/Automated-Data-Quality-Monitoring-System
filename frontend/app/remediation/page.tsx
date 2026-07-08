"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import type { ColumnDef } from "@tanstack/react-table"
import { AlertTriangle, CheckCircle2, ClipboardCheck, ShieldAlert, UserPlus, Wrench, XCircle } from "lucide-react"

import { CleaningJobWizard } from "@/components/remediation/cleaning-job-wizard"
import { ChangeHistoryTable } from "@/components/remediation/change-history-table"
import { IssueDetailDrawer } from "@/components/remediation/issue-detail-drawer"
import { IssueStatusBadge } from "@/components/remediation/issue-status-badge"
import { JobStatusBadge } from "@/components/remediation/job-status-badge"
import { RemediationAction, RemediationActionDialog } from "@/components/remediation/remediation-action-dialog"
import { RemediationAssignDialog } from "@/components/remediation/remediation-assign-dialog"
import { AppShell } from "@/components/app-shell"
import { DataTableColumnHeader } from "@/components/data-table/data-table-column-header"
import { EnterpriseDataTable } from "@/components/data-table/data-table"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { PageHeader } from "@/components/ui-custom/page-header"
import { SeverityBadge } from "@/components/ui-custom/severity-badge"
import { api, getStoredUserRole } from "@/lib/api-client"
import { REMEDIATION_PERMISSIONS } from "@/lib/constants"
import { formatDateTime } from "@/lib/formatters"
import type {
  CleanableIssue,
  CleaningChangeLog,
  CleaningJob,
  CleaningSuggestion,
  ProposedCleaningChange,
  AppUser,
} from "@/lib/types"

function hasPermission(role: string, permission: string) {
  return ((REMEDIATION_PERMISSIONS as Record<string, readonly string[]>)[role] ?? []).includes(permission)
}

export default function RemediationPage() {
  const [issues, setIssues] = useState<CleanableIssue[]>([])
  const [jobs, setJobs] = useState<CleaningJob[]>([])
  const [selectedIssue, setSelectedIssue] = useState<CleanableIssue | undefined>()
  const [suggestions, setSuggestions] = useState<CleaningSuggestion[]>([])
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [assignDialogOpen, setAssignDialogOpen] = useState(false)
  const [assignIssue, setAssignIssue] = useState<CleanableIssue | undefined>()
  const [assignUsers, setAssignUsers] = useState<AppUser[]>([])
  const [selectedAssignee, setSelectedAssignee] = useState("")
  const [assignUsersLoading, setAssignUsersLoading] = useState(false)
  const [assignSaving, setAssignSaving] = useState(false)
  const [assignError, setAssignError] = useState("")
  const [activeTab, setActiveTab] = useState("open")
  const [actionDialogOpen, setActionDialogOpen] = useState(false)
  const [actionJob, setActionJob] = useState<CleaningJob | undefined>()
  const [actionType, setActionType] = useState<RemediationAction>("approve")
  const [actionSaving, setActionSaving] = useState(false)
  const [actionError, setActionError] = useState("")
  const [message, setMessage] = useState("")
  const [loading, setLoading] = useState(true)
  const role = getStoredUserRole()
  const canEdit = hasPermission(role, "create_cleaning_job")
  const canApprove = hasPermission(role, "approve_cleaning_job")
  const canAssign = hasPermission(role, "assign_issues")
  const canExecuteApproved = hasPermission(role, "execute_cleaning_job") || hasPermission(role, "execute_approved_cleaning_job")
  const canRollback = hasPermission(role, "rollback_cleaning_job")
  const isScopedAnalyst = role === "data_analyst"

  const loadData = useCallback(async () => {
    setLoading(true)
    setMessage("")
    try {
      const [issueRows, jobRows] = await Promise.all([
        api.cleanableIssues(),
        api.cleaningJobs().catch(() => []),
      ])
      setIssues(issueRows)
      setJobs(jobRows)
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Unable to load remediation data.")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  const openIssue = useCallback(async (issue: CleanableIssue) => {
    setSelectedIssue(issue)
    setDrawerOpen(true)
    try {
      const result = await api.cleaningSuggestions(Number(issue.id))
      setSuggestions(result.suggestions)
    } catch {
      setSuggestions([])
    }
  }, [])

  const suggestFix = useCallback(async (issue: CleanableIssue) => {
    setSelectedIssue(issue)
    setActiveTab("suggested")
    setMessage(`Loading suggested actions for issue #${issue.id}...`)
    try {
      const result = await api.cleaningSuggestions(Number(issue.id))
      setSuggestions(result.suggestions)
      setMessage(
        `Issue #${issue.id} selected. Choose an action in the Cleaning Job Wizard, preview it, then create a job.`
      )
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not load suggestions.")
    }
  }, [])

  const updateStatus = useCallback(async (issue: CleanableIssue, status: string) => {
    try {
      await api.updateIssueStatus(Number(issue.id), { status, notes: `Updated from remediation center.` })
      setMessage(`Issue #${issue.id} marked ${status}.`)
      await loadData()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not update issue status.")
    }
  }, [loadData])

  async function loadAssignableUsers(preferredAssignee?: string) {
    setAssignUsersLoading(true)
    setAssignError("")
    try {
      const users = await api.users()
      const activeUsers = users.filter((user) => user.is_active !== false)
      const preferred =
        activeUsers.find((user) => user.username === preferredAssignee)?.username ||
        activeUsers.find((user) => ["analyst", "data_analyst", "data_engineer"].includes(String(user.role)))?.username ||
        activeUsers[0]?.username ||
        ""
      setAssignUsers(users)
      setSelectedAssignee(preferred)
    } catch (err) {
      setAssignError(
        err instanceof Error
          ? err.message
          : "Unable to load users. Admin access is required to retrieve dashboard users."
      )
    } finally {
      setAssignUsersLoading(false)
    }
  }

  const openAssignDialog = useCallback((issue: CleanableIssue) => {
    setAssignIssue(issue)
    setSelectedAssignee(issue.assigned_to || "")
    setAssignError("")
    setAssignDialogOpen(true)
    loadAssignableUsers(issue.assigned_to)
  }, [])

  const submitAssignIssue = useCallback(async () => {
    if (!assignIssue || !selectedAssignee) return
    setAssignSaving(true)
    setAssignError("")
    try {
      await api.updateIssueStatus(Number(assignIssue.id), {
        status: "ASSIGNED",
        assigned_to: selectedAssignee,
        notes: `Assigned from remediation center.`,
      })
      setMessage(`Issue #${assignIssue.id} assigned to ${selectedAssignee}.`)
      setAssignDialogOpen(false)
      await loadData()
    } catch (err) {
      setAssignError(err instanceof Error ? err.message : "Could not assign issue.")
    } finally {
      setAssignSaving(false)
    }
  }, [assignIssue, loadData, selectedAssignee])

  const openJobActionDialog = useCallback((job: CleaningJob, action: RemediationAction) => {
    setActionJob(job)
    setActionType(action)
    setActionError("")
    setActionDialogOpen(true)
  }, [])

  const approveJob = useCallback(async (job: CleaningJob) => {
    try {
      await api.approveCleaningJob(job.id)
      setMessage(`Cleaning job #${job.id} approved.`)
      setActionDialogOpen(false)
      await loadData()
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Could not approve job.")
    }
  }, [loadData])

  const executeJob = useCallback(async (job: CleaningJob) => {
    try {
      await api.executeCleaningJob(job.id)
      setMessage(`Cleaning job #${job.id} executed.`)
      setActionDialogOpen(false)
      await loadData()
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Could not execute job.")
    }
  }, [loadData])

  const rollbackJob = useCallback(async (job: CleaningJob) => {
    try {
      await api.rollbackCleaningJob(job.id)
      setMessage(`Cleaning job #${job.id} rolled back.`)
      setActionDialogOpen(false)
      await loadData()
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Could not rollback job.")
    }
  }, [loadData])

  const confirmJobAction = useCallback(async () => {
    if (!actionJob) return
    setActionSaving(true)
    setActionError("")
    try {
      if (actionType === "approve") {
        await approveJob(actionJob)
      } else if (actionType === "execute") {
        await executeJob(actionJob)
      } else {
        await rollbackJob(actionJob)
      }
    } finally {
      setActionSaving(false)
    }
  }, [actionJob, actionType, approveJob, executeJob, rollbackJob])

  const openIssues = issues.filter((issue) => !["FALSE_POSITIVE", "IGNORED", "RESOLVED", "FIX_APPLIED"].includes(issue.issue_status || "OPEN"))
  const fixProposed = issues.filter((issue) => issue.issue_status === "FIX_PROPOSED")
  const fixApplied = issues.filter((issue) => issue.issue_status === "FIX_APPLIED")
  const falsePositive = issues.filter((issue) => issue.issue_status === "FALSE_POSITIVE")
  const ignored = issues.filter((issue) => issue.issue_status === "IGNORED")
  const pendingApproval = jobs.filter((job) => job.status === "PENDING_APPROVAL")
  const failedJobs = jobs.filter((job) => job.status === "FAILED")
  const changeHistory = jobs.flatMap((job) => job.change_log ?? []) as CleaningChangeLog[]

  const issueColumns = useMemo<ColumnDef<CleanableIssue>[]>(
    () => [
      { accessorKey: "id", header: ({ column }) => <DataTableColumnHeader column={column} title="Issue ID" /> },
      { accessorKey: "run_id", header: "Run" },
      { accessorKey: "dataset_name", header: "Dataset" },
      { accessorKey: "check_type", header: "Check Type" },
      { accessorKey: "column_name", header: "Column" },
      { accessorKey: "row_identifier", header: "Row Identifier" },
      { accessorKey: "bad_value", header: "Bad Value" },
      { accessorKey: "reason", header: "Reason", cell: ({ row }) => <span className="block max-w-lg whitespace-normal">{row.original.reason}</span> },
      { accessorKey: "severity", header: "Severity", cell: ({ row }) => <SeverityBadge severity={row.original.severity} /> },
      { accessorKey: "issue_status", header: "Issue Status", cell: ({ row }) => <IssueStatusBadge status={row.original.issue_status} /> },
      { accessorKey: "assigned_to", header: "Assigned To" },
      {
        id: "actions",
        header: "Actions",
        cell: ({ row }) => (
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="outline" onClick={() => openIssue(row.original)}>View</Button>
            {canAssign ? (
              <Button size="sm" variant="outline" onClick={() => openAssignDialog(row.original)}>
                <UserPlus className="size-4" />
                Assign
              </Button>
            ) : null}
            <Button size="sm" variant="outline" onClick={() => suggestFix(row.original)} disabled={!canEdit}>Suggest</Button>
            <Button size="sm" variant="outline" onClick={() => updateStatus(row.original, "FALSE_POSITIVE")} disabled={!canEdit}>False Positive</Button>
            <Button size="sm" onClick={() => suggestFix(row.original)} disabled={!canEdit}>Create Job</Button>
          </div>
        ),
      },
    ],
    [canAssign, canEdit, openAssignDialog, openIssue, suggestFix, updateStatus]
  )

  const jobColumns = useMemo<ColumnDef<CleaningJob>[]>(
    () => [
      { accessorKey: "id", header: "Job ID" },
      { accessorKey: "dataset_name", header: "Dataset" },
      { accessorKey: "cleaning_action", header: "Action" },
      { accessorKey: "target_table", header: "Table" },
      { accessorKey: "target_column", header: "Column" },
      {
        id: "proposed_changes",
        header: "Proposed Change",
        cell: ({ row }) => <ProposedChangesCell job={row.original} />,
      },
      { accessorKey: "status", header: "Status", cell: ({ row }) => <JobStatusBadge status={row.original.status} /> },
      { accessorKey: "requested_by", header: "Requested By" },
      { accessorKey: "created_at", header: "Created", cell: ({ row }) => formatDateTime(row.original.created_at) },
      {
        id: "actions",
        header: "Actions",
        cell: ({ row }) => (
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="outline" disabled={!canApprove || row.original.status !== "PENDING_APPROVAL"} onClick={() => openJobActionDialog(row.original, "approve")}>Approve</Button>
            <Button size="sm" variant="outline" disabled={!canExecuteApproved || (row.original.status !== "APPROVED" && row.original.status !== "READY_FOR_EXECUTION")} onClick={() => openJobActionDialog(row.original, "execute")}>Execute</Button>
            <Button size="sm" variant="outline" disabled={!canRollback || row.original.status !== "EXECUTED"} onClick={() => openJobActionDialog(row.original, "rollback")}>Rollback</Button>
          </div>
        ),
      },
    ],
    [canApprove, canExecuteApproved, canRollback, openJobActionDialog]
  )

  return (
    <AppShell>
      <PageHeader
        eyebrow="Operations"
        title="Data Remediation Center"
        subtitle="Preview, propose, approve, execute, audit, and roll back safe data cleaning actions."
        onRefresh={loadData}
      />

      {!canEdit ? (
        <Card className="rounded-xl border-amber-100 bg-amber-50">
          <CardContent className="p-4 text-sm text-amber-800">You have view-only access.</CardContent>
        </Card>
      ) : null}
      {isScopedAnalyst ? (
        <Card className="rounded-xl border-blue-100 bg-blue-50">
          <CardContent className="p-4 text-sm text-blue-700">
            Your remediation queue shows only issues and cleaning jobs assigned to you.
          </CardContent>
        </Card>
      ) : null}
      {message ? (
        <Card className="rounded-xl border-blue-100 bg-blue-50">
          <CardContent className="p-4 text-sm text-blue-700">{message}</CardContent>
        </Card>
      ) : null}

      <div className="grid gap-4 md:grid-cols-3 xl:grid-cols-6">
        <EnterpriseMetric title="Open Issues" value={openIssues.length} icon={ShieldAlert} tone="blue" />
        <EnterpriseMetric title="Fix Proposed" value={fixProposed.length} icon={Wrench} tone="amber" />
        <EnterpriseMetric title="Pending Approval" value={pendingApproval.length} icon={ClipboardCheck} tone="amber" />
        <EnterpriseMetric title="Fix Applied" value={fixApplied.length} icon={CheckCircle2} tone="green" />
        <EnterpriseMetric title="False Positives" value={falsePositive.length} icon={XCircle} tone="slate" />
        <EnterpriseMetric title="Jobs Failed" value={failedJobs.length} icon={AlertTriangle} tone="red" />
      </div>

      <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value ?? "open")}>
        <TabsList className="flex flex-wrap">
          <TabsTrigger value="open">Open Issues</TabsTrigger>
          <TabsTrigger value="suggested">Suggested Fixes</TabsTrigger>
          <TabsTrigger value="jobs">Cleaning Jobs</TabsTrigger>
          <TabsTrigger value="approval">Pending Approval</TabsTrigger>
          <TabsTrigger value="history">Change History</TabsTrigger>
          <TabsTrigger value="closed">False Positives / Ignored</TabsTrigger>
        </TabsList>
        <TabsContent value="open" className="mt-5">
          <EnterpriseDataTable columns={issueColumns} data={openIssues} loading={loading} />
        </TabsContent>
        <TabsContent value="suggested" className="mt-5 grid gap-6 xl:grid-cols-[1fr_520px]">
          <EnterpriseDataTable columns={issueColumns} data={selectedIssue ? [selectedIssue] : openIssues.slice(0, 10)} loading={loading} />
          <CleaningJobWizard issue={selectedIssue} suggestions={suggestions} onJobCreated={loadData} />
        </TabsContent>
        <TabsContent value="jobs" className="mt-5">
          <EnterpriseDataTable columns={jobColumns} data={jobs} loading={loading} />
        </TabsContent>
        <TabsContent value="approval" className="mt-5">
          <EnterpriseDataTable columns={jobColumns} data={pendingApproval} loading={loading} />
        </TabsContent>
        <TabsContent value="history" className="mt-5">
          <ChangeHistoryTable rows={changeHistory} />
        </TabsContent>
        <TabsContent value="closed" className="mt-5">
          <EnterpriseDataTable columns={issueColumns} data={[...falsePositive, ...ignored]} loading={loading} />
        </TabsContent>
      </Tabs>

      <IssueDetailDrawer
        issue={selectedIssue}
        open={drawerOpen}
        suggestions={suggestions}
        onOpenChange={setDrawerOpen}
        onCreateJob={(issue) => {
          setDrawerOpen(false)
          suggestFix(issue)
        }}
        onStatusChange={updateStatus}
      />
      <RemediationActionDialog
        job={actionJob}
        action={actionType}
        open={actionDialogOpen}
        saving={actionSaving}
        error={actionError}
        onOpenChange={setActionDialogOpen}
        onConfirm={confirmJobAction}
      />
      <RemediationAssignDialog
        issue={assignIssue}
        users={assignUsers}
        open={assignDialogOpen}
        loading={assignUsersLoading}
        saving={assignSaving}
        selectedUsername={selectedAssignee}
        error={assignError}
        onOpenChange={setAssignDialogOpen}
        onSelectedUsernameChange={setSelectedAssignee}
        onAssign={submitAssignIssue}
      />
    </AppShell>
  )
}

function ProposedChangesCell({ job }: { job: CleaningJob }) {
  const proposed = job.proposed_changes ?? []

  if (!proposed.length) {
    return (
      <div className="max-w-md text-sm text-slate-500">
        {job.new_value ? `Set ${job.target_column ?? "value"} to ${job.new_value}` : "No preview rows recorded"}
      </div>
    )
  }

  return (
    <div className="max-w-xl space-y-2">
      {proposed.slice(0, 3).map((change: ProposedCleaningChange, index: number) => (
        <div key={`${change.row_identifier}-${index}`} className="rounded-lg border bg-slate-50 p-2 text-xs">
          <div className="font-medium text-slate-700">
            {change.table_name}.{change.column_name} · {change.row_identifier}
          </div>
          <div className="mt-1 grid gap-1 sm:grid-cols-[1fr_auto_1fr]">
            <span className="truncate rounded-md bg-white px-2 py-1 text-slate-600" title={String(change.old_value ?? "")}>
              {String(change.old_value ?? "NULL")}
            </span>
            <span className="self-center text-slate-400">to</span>
            <span className="truncate rounded-md bg-white px-2 py-1 font-medium text-slate-900" title={String(change.new_value ?? "")}>
              {String(change.new_value ?? "NULL")}
            </span>
          </div>
        </div>
      ))}
      {proposed.length > 3 ? <div className="text-xs text-slate-500">+{proposed.length - 3} more proposed row(s)</div> : null}
    </div>
  )
}

function EnterpriseMetric({
  title,
  value,
  icon,
}: {
  title: string
  value: number
  icon: typeof ShieldAlert
  tone: "blue" | "green" | "amber" | "red" | "slate"
}) {
  const Icon = icon
  return (
    <div>
      <Card className="rounded-xl shadow-sm">
        <CardContent className="p-5">
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</div>
              <div className="mt-2 text-2xl font-semibold">{value}</div>
            </div>
            <Icon className="size-5 text-slate-500" />
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

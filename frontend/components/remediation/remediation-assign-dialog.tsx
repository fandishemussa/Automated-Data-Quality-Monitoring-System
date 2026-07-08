"use client"

import { AlertCircle, FileWarning, UserCheck, UsersRound } from "lucide-react"

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { IssueStatusBadge } from "@/components/remediation/issue-status-badge"
import { SeverityBadge } from "@/components/ui-custom/severity-badge"
import { StatusBadge } from "@/components/ui-custom/status-badge"
import type { AppUser, CleanableIssue } from "@/lib/types"

type RemediationAssignDialogProps = {
  issue?: CleanableIssue
  users: AppUser[]
  open: boolean
  loading?: boolean
  saving?: boolean
  selectedUsername: string
  error?: string
  onOpenChange: (open: boolean) => void
  onSelectedUsernameChange: (username: string) => void
  onAssign: () => void
}

export function RemediationAssignDialog({
  issue,
  users,
  open,
  loading = false,
  saving = false,
  selectedUsername,
  error,
  onOpenChange,
  onSelectedUsernameChange,
  onAssign,
}: RemediationAssignDialogProps) {
  const activeUsers = users.filter((user) => user.is_active !== false)
  const selectedUser = activeUsers.find((user) => user.username === selectedUsername)
  const analystCount = activeUsers.filter((user) => ["analyst", "data_analyst"].includes(String(user.role))).length

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl p-0 sm:max-w-2xl">
        <DialogHeader className="border-b p-5">
          <div className="flex items-start gap-3">
            <div className="flex size-10 items-center justify-center rounded-xl bg-blue-50 text-blue-700">
              <UserCheck className="size-5" />
            </div>
            <div>
              <DialogTitle>Assign Remediation Issue</DialogTitle>
              <DialogDescription className="mt-1">
                Assign this issue to an active analyst or data owner for follow-up.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="grid gap-5 p-5">
          {issue ? (
            <div className="rounded-xl border bg-slate-50 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="text-sm font-semibold text-slate-950">Issue #{issue.id}</div>
                  <div className="mt-1 text-xs uppercase tracking-wide text-slate-500">
                    {issue.dataset_name}.{issue.column_name}
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <SeverityBadge severity={issue.severity} />
                  <IssueStatusBadge status={issue.issue_status} />
                </div>
              </div>
              <p className="mt-3 text-sm leading-6 text-slate-600">{issue.reason}</p>
              <div className="mt-3 grid gap-2 text-xs text-slate-500 sm:grid-cols-3">
                <div>Check: {issue.check_type || "N/A"}</div>
                <div>Row: {issue.row_identifier || "N/A"}</div>
                <div>Current assignee: {issue.assigned_to || "None"}</div>
              </div>
            </div>
          ) : null}

          <div className="grid gap-2">
            <Label htmlFor="remediation-assignee">Assignee</Label>
            <select
              id="remediation-assignee"
              className="h-10 rounded-lg border border-slate-200 bg-white px-3 text-sm shadow-sm outline-none transition focus:border-blue-400 focus:ring-3 focus:ring-blue-100"
              disabled={loading || saving || !activeUsers.length}
              value={selectedUsername}
              onChange={(event) => onSelectedUsernameChange(event.target.value)}
            >
              <option value="">{loading ? "Loading users..." : "Select a user"}</option>
              {activeUsers.map((user) => (
                <option key={user.id} value={user.username}>
                  {user.full_name || user.username} · {user.role}
                </option>
              ))}
            </select>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <SummaryTile icon={UsersRound} label="Active Users" value={String(activeUsers.length)} />
            <SummaryTile icon={UserCheck} label="Analysts" value={String(analystCount)} />
            <SummaryTile icon={FileWarning} label="Run" value={String(issue?.run_id ?? "N/A")} />
          </div>

          {selectedUser ? (
            <div className="rounded-xl border border-blue-100 bg-blue-50 p-4">
              <div className="text-sm font-semibold text-blue-950">{selectedUser.full_name || selectedUser.username}</div>
              <div className="mt-1 text-sm text-blue-700">{selectedUser.email || "No email recorded"}</div>
              <div className="mt-3 flex flex-wrap gap-2">
                <StatusBadge status={selectedUser.role} />
                <StatusBadge status={selectedUser.department || "No department"} />
              </div>
            </div>
          ) : null}

          {error ? (
            <div className="flex items-start gap-2 rounded-xl border border-red-100 bg-red-50 p-3 text-sm text-red-700">
              <AlertCircle className="mt-0.5 size-4 shrink-0" />
              <span>{error}</span>
            </div>
          ) : null}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={onAssign} disabled={!selectedUsername || saving || loading}>
            {saving ? "Assigning..." : "Assign Issue"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function SummaryTile({
  icon,
  label,
  value,
}: {
  icon: typeof UsersRound
  label: string
  value: string
}) {
  const Icon = icon
  return (
    <div className="rounded-xl border bg-white p-3">
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
        <Icon className="size-4" /> {label}
      </div>
      <div className="mt-2 text-xl font-semibold">{value}</div>
    </div>
  )
}

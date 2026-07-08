"use client"

import { AlertCircle, BellRing, UserCheck, UsersRound } from "lucide-react"

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
import { StatusBadge } from "@/components/ui-custom/status-badge"
import type { AlertRecord, AppUser } from "@/lib/types"

type AlertAssignDialogProps = {
  alert?: AlertRecord
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

export function AlertAssignDialog({
  alert,
  users,
  open,
  loading = false,
  saving = false,
  selectedUsername,
  error,
  onOpenChange,
  onSelectedUsernameChange,
  onAssign,
}: AlertAssignDialogProps) {
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
              <DialogTitle>Assign Alert Ownership</DialogTitle>
              <DialogDescription className="mt-1">
                Select an active dashboard user to own follow-up for this alert.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="grid gap-5 p-5">
          {alert ? (
            <div className="rounded-xl border bg-slate-50 p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="text-sm font-semibold text-slate-950">Alert #{alert.id}</div>
                  <div className="mt-1 text-xs uppercase tracking-wide text-slate-500">
                    {alert.alert_type ?? "Data quality alert"}
                  </div>
                </div>
                <div className="flex gap-2">
                  <StatusBadge status={alert.severity} />
                  <StatusBadge status={alert.is_resolved ? "RESOLVED" : alert.escalation_status || "OPEN"} />
                </div>
              </div>
              <p className="mt-3 text-sm leading-6 text-slate-600">{alert.message}</p>
              <div className="mt-3 grid gap-2 text-xs text-slate-500 sm:grid-cols-3">
                <div>Owner team: {alert.owner_team || "Unassigned"}</div>
                <div>Current assignee: {alert.assigned_to || "None"}</div>
                <div>Run: {alert.run_id ?? "N/A"}</div>
              </div>
            </div>
          ) : null}

          <div className="grid gap-2">
            <Label htmlFor="alert-assignee">Assignee</Label>
            <select
              id="alert-assignee"
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
            <div className="rounded-xl border bg-white p-3">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                <UsersRound className="size-4" /> Active Users
              </div>
              <div className="mt-2 text-2xl font-semibold">{activeUsers.length}</div>
            </div>
            <div className="rounded-xl border bg-white p-3">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                <UserCheck className="size-4" /> Analysts
              </div>
              <div className="mt-2 text-2xl font-semibold">{analystCount}</div>
            </div>
            <div className="rounded-xl border bg-white p-3">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                <BellRing className="size-4" /> Severity
              </div>
              <div className="mt-2">
                <StatusBadge status={alert?.severity ?? "UNKNOWN"} />
              </div>
            </div>
          </div>

          {selectedUser ? (
            <div className="rounded-xl border border-blue-100 bg-blue-50 p-4">
              <div className="text-sm font-semibold text-blue-950">{selectedUser.full_name || selectedUser.username}</div>
              <div className="mt-1 text-sm text-blue-700">{selectedUser.email || "No email recorded"}</div>
              <div className="mt-3 flex flex-wrap gap-2">
                <StatusBadge status={selectedUser.role} />
                <StatusBadge status={selectedUser.is_active === false ? "Inactive" : "Active"} />
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
            {saving ? "Assigning..." : "Assign Alert"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

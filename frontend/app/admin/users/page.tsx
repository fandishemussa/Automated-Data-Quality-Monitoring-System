"use client"

import { FormEvent, useEffect, useState } from "react"
import type { ColumnDef } from "@tanstack/react-table"
import { CheckCircle2, ShieldAlert, UserPlus, UsersRound, XCircle } from "lucide-react"

import { AppShell } from "@/components/app-shell"
import { EnterpriseDataTable } from "@/components/data-table/data-table"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { StatusBadge } from "@/components/ui-custom/status-badge"
import { PageHeader } from "@/components/ui-custom/page-header"
import { api, getStoredUserRole } from "@/lib/api-client"
import { formatDateTime } from "@/lib/formatters"
import type { AppUser, CreateUserPayload, ProfileUpdateRequest, UserRole } from "@/lib/types"

const roles: UserRole[] = ["admin", "analyst", "data_analyst", "data_engineer", "viewer"]

const emptyForm: CreateUserPayload = {
  username: "",
  password: "",
  full_name: "",
  email: "",
  role: "viewer",
  is_active: true,
}

export default function UserManagementPage() {
  const [users, setUsers] = useState<AppUser[]>([])
  const [profileUpdates, setProfileUpdates] = useState<ProfileUpdateRequest[]>([])
  const [form, setForm] = useState<CreateUserPayload>(emptyForm)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState("")
  const [error, setError] = useState("")
  const role = getStoredUserRole()
  const isAdmin = role === "admin"

  async function loadUsers() {
    setLoading(true)
    setError("")
    try {
      setUsers(await api.users())
      setProfileUpdates(await api.profileUpdateRequests())
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load users.")
    } finally {
      setLoading(false)
    }
  }

  async function reviewProfileUpdate(update: ProfileUpdateRequest, action: "approve" | "reject") {
    setError("")
    setMessage("")
    try {
      if (action === "approve") {
        await api.approveProfileUpdate(update.id, "Approved from User Management.")
        setMessage(`Approved profile update #${update.id}.`)
      } else {
        await api.rejectProfileUpdate(update.id, "Rejected from User Management.")
        setMessage(`Rejected profile update #${update.id}.`)
      }
      await loadUsers()
    } catch (err) {
      setError(err instanceof Error ? err.message : `Unable to ${action} profile update.`)
    }
  }

  useEffect(() => {
    if (isAdmin) {
      loadUsers()
    } else {
      setLoading(false)
    }
  }, [isAdmin])

  async function createDashboardUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaving(true)
    setError("")
    setMessage("")
    try {
      await api.createUser(form)
      setMessage(`Created user ${form.username}.`)
      setForm(emptyForm)
      await loadUsers()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create user.")
    } finally {
      setSaving(false)
    }
  }

  async function toggleUser(user: AppUser) {
    setError("")
    setMessage("")
    try {
      const updated = await api.updateUser(user.id, { is_active: !user.is_active })
      setMessage(`${updated.username} is now ${updated.is_active ? "active" : "inactive"}.`)
      await loadUsers()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update user.")
    }
  }

  const columns: ColumnDef<AppUser>[] = [
    { accessorKey: "username", header: "Username" },
    { accessorKey: "full_name", header: "Name" },
    { accessorKey: "email", header: "Email" },
    { accessorKey: "job_title", header: "Job Title" },
    { accessorKey: "department", header: "Department" },
    {
      accessorKey: "profile_completion_percent",
      header: "Profile",
      cell: ({ row }) => `${row.original.profile_completion_percent ?? 0}%`,
    },
    {
      accessorKey: "role",
      header: "Role",
      cell: ({ row }) => <StatusBadge status={row.original.role} />,
    },
    {
      accessorKey: "is_active",
      header: "Status",
      cell: ({ row }) => <StatusBadge status={row.original.is_active ? "Active" : "Inactive"} />,
    },
    {
      accessorKey: "last_login_at",
      header: "Last Login",
      cell: ({ row }) => formatDateTime(row.original.last_login_at),
    },
    {
      id: "actions",
      header: "Actions",
      cell: ({ row }) => (
        <Button size="sm" variant="outline" onClick={() => toggleUser(row.original)}>
          {row.original.is_active ? "Deactivate" : "Activate"}
        </Button>
      ),
    },
  ]

  const profileUpdateColumns: ColumnDef<ProfileUpdateRequest>[] = [
    { accessorKey: "id", header: "Request" },
    { accessorKey: "username", header: "User" },
    {
      accessorKey: "requested_changes",
      header: "Requested Changes",
      cell: ({ row }) => <RequestedChanges update={row.original} />,
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => <StatusBadge status={row.original.status} />,
    },
    {
      accessorKey: "submitted_at",
      header: "Submitted",
      cell: ({ row }) => formatDateTime(row.original.submitted_at),
    },
    {
      id: "actions",
      header: "Actions",
      cell: ({ row }) =>
        row.original.status !== "PENDING" ? null : (
          <div className="flex flex-wrap gap-2">
            <Button size="sm" onClick={() => reviewProfileUpdate(row.original, "approve")}>
              <CheckCircle2 className="size-4" />
              Approve
            </Button>
            <Button size="sm" variant="outline" onClick={() => reviewProfileUpdate(row.original, "reject")}>
              <XCircle className="size-4" />
              Reject
            </Button>
          </div>
        ),
    },
  ]

  return (
    <AppShell>
      <PageHeader
        eyebrow="Administration"
        title="User Management"
        subtitle="Create dashboard users and assign admin, analyst, data engineer, or viewer roles."
        onRefresh={isAdmin ? loadUsers : undefined}
      />

      {!isAdmin ? (
        <Alert variant="destructive">
          <ShieldAlert className="size-4" />
          <AlertTitle>Admin access required</AlertTitle>
          <AlertDescription>Only admin users can view and manage dashboard users.</AlertDescription>
        </Alert>
      ) : (
        <div className="grid gap-6 xl:grid-cols-[420px_1fr]">
          <Card className="rounded-xl shadow-sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <UserPlus className="size-5" /> Create User
              </CardTitle>
              <CardDescription>New users can log in immediately after creation.</CardDescription>
            </CardHeader>
            <CardContent>
              <form className="space-y-4" onSubmit={createDashboardUser}>
                <div className="grid gap-2">
                  <Label htmlFor="username">Username</Label>
                  <Input
                    id="username"
                    value={form.username}
                    onChange={(event) => setForm((current) => ({ ...current, username: event.target.value }))}
                    required
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="full-name">Full name</Label>
                  <Input
                    id="full-name"
                    value={form.full_name}
                    onChange={(event) => setForm((current) => ({ ...current, full_name: event.target.value }))}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    value={form.email}
                    onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="password">Temporary password</Label>
                  <Input
                    id="password"
                    type="password"
                    value={form.password}
                    onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))}
                    required
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="role">Role</Label>
                  <select
                    id="role"
                    className="h-9 rounded-lg border border-input bg-white px-3 text-sm"
                    value={form.role}
                    onChange={(event) => setForm((current) => ({ ...current, role: event.target.value as UserRole }))}
                  >
                    {roles.map((item) => (
                      <option key={item} value={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                </div>
                <Button className="w-full" disabled={saving} type="submit">
                  <UsersRound className="size-4" />
                  {saving ? "Creating..." : "Create User"}
                </Button>
              </form>
            </CardContent>
          </Card>

          <div className="space-y-4">
            {message ? (
              <Alert>
                <AlertTitle>Updated</AlertTitle>
                <AlertDescription>{message}</AlertDescription>
              </Alert>
            ) : null}
            {error ? (
              <Alert variant="destructive">
                <AlertTitle>Request failed</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            ) : null}
            <EnterpriseDataTable
              columns={columns}
              data={users}
              loading={loading}
              searchPlaceholder="Search users..."
              emptyTitle="No users found"
              emptyDescription="Create the first dashboard user from the form."
            />
          </div>
        </div>
      )}

      {isAdmin ? (
        <Card className="rounded-xl shadow-sm">
          <CardHeader>
            <CardTitle>Profile Update Approval Queue</CardTitle>
            <CardDescription>Review user-submitted profile completion changes before they update the users table.</CardDescription>
          </CardHeader>
          <CardContent>
            <EnterpriseDataTable
              columns={profileUpdateColumns}
              data={profileUpdates}
              loading={loading}
              searchPlaceholder="Search profile updates..."
              emptyTitle="No profile update requests"
              emptyDescription="Submitted profile changes will appear here for admin approval."
            />
          </CardContent>
        </Card>
      ) : null}
    </AppShell>
  )
}

function RequestedChanges({ update }: { update: ProfileUpdateRequest }) {
  const changes = Object.entries(update.requested_changes ?? {})
  if (!changes.length) {
    return <span className="text-sm text-slate-500">No changes</span>
  }

  return (
    <div className="grid max-w-2xl gap-2">
      {changes.map(([field, nextValue]) => {
        const currentValue = currentProfileValue(update, field)
        return (
          <div key={field} className="rounded-lg border bg-slate-50 p-2 text-xs">
            <div className="font-semibold uppercase tracking-wide text-slate-500">{field.replaceAll("_", " ")}</div>
            <div className="mt-1 grid gap-1 md:grid-cols-[1fr_auto_1fr]">
              <span className="truncate rounded-md bg-white px-2 py-1" title={String(currentValue ?? "")}>
                {String(currentValue || "Blank")}
              </span>
              <span className="self-center text-slate-400">to</span>
              <span className="truncate rounded-md bg-white px-2 py-1 font-medium text-slate-900" title={String(nextValue ?? "")}>
                {String(nextValue || "Blank")}
              </span>
            </div>
          </div>
        )
      })}
    </div>
  )
}

function currentProfileValue(update: ProfileUpdateRequest, field: string) {
  const key = `current_${field}` as keyof ProfileUpdateRequest
  return update[key]
}

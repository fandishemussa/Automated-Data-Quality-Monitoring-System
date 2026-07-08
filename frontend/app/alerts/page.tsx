"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import type { ColumnDef } from "@tanstack/react-table"
import { AlertTriangle, BellRing, CheckCircle2, ShieldAlert } from "lucide-react"

import { AlertCard } from "@/components/alerts/alert-card"
import { AlertFilters, AlertFiltersPanel } from "@/components/alerts/alert-filters"
import { AlertAssignDialog } from "@/components/alerts/alert-assign-dialog"
import { AlertTimeline } from "@/components/alerts/alert-timeline"
import { DataTableColumnHeader } from "@/components/data-table/data-table-column-header"
import { EnterpriseDataTable } from "@/components/data-table/data-table"
import { AppShell } from "@/components/app-shell"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { EnterpriseMetricCard } from "@/components/ui-custom/metric-card"
import { PageHeader } from "@/components/ui-custom/page-header"
import { SeverityBadge } from "@/components/ui-custom/severity-badge"
import { StatusBadge } from "@/components/ui-custom/status-badge"
import { api, getStoredUserRole } from "@/lib/api-client"
import { formatDateTime } from "@/lib/formatters"
import type { AlertRecord, AppUser } from "@/lib/types"

const initialFilters: AlertFilters = {
  search: "",
  severity: "ALL",
  status: "ALL",
  ownerTeam: "",
  assignedTo: "",
}

function alertStatus(alert: AlertRecord) {
  if (alert.is_resolved) return "RESOLVED"
  if (alert.escalation_status) return alert.escalation_status
  return "OPEN"
}

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<AlertRecord[]>([])
  const [filters, setFilters] = useState(initialFilters)
  const [selectedAlert, setSelectedAlert] = useState<AlertRecord | undefined>()
  const [assignAlertTarget, setAssignAlertTarget] = useState<AlertRecord | undefined>()
  const [assignDialogOpen, setAssignDialogOpen] = useState(false)
  const [assignUsers, setAssignUsers] = useState<AppUser[]>([])
  const [selectedAssignee, setSelectedAssignee] = useState("")
  const [assignError, setAssignError] = useState("")
  const [assignUsersLoading, setAssignUsersLoading] = useState(false)
  const [assignSaving, setAssignSaving] = useState(false)
  const [message, setMessage] = useState("")
  const [loading, setLoading] = useState(true)
  const role = getStoredUserRole()
  const canAssignAlerts = role === "admin"

  async function loadAlerts() {
    setLoading(true)
    setMessage("")
    try {
      setAlerts(await api.alerts())
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Unable to load alerts.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadAlerts()
  }, [])

  const filteredAlerts = alerts.filter((alert) => {
    const blob = JSON.stringify(alert).toLowerCase()
    const status = alertStatus(alert)
    return (
      (!filters.search || blob.includes(filters.search.toLowerCase())) &&
      (filters.severity === "ALL" || alert.severity === filters.severity) &&
      (filters.status === "ALL" || status === filters.status) &&
      (!filters.ownerTeam || String(alert.owner_team ?? "").toLowerCase().includes(filters.ownerTeam.toLowerCase())) &&
      (!filters.assignedTo || String(alert.assigned_to ?? "").toLowerCase().includes(filters.assignedTo.toLowerCase()))
    )
  })

  const openAlerts = alerts.filter((alert) => !alert.is_resolved)
  const criticalAlerts = alerts.filter((alert) => alert.severity === "CRITICAL")
  const resolvedAlerts = alerts.filter((alert) => alert.is_resolved)
  const escalatedAlerts = alerts.filter((alert) => alert.escalation_status === "ESCALATED" || alert.escalated_at)

  const replaceAlert = useCallback((updated: AlertRecord) => {
    setAlerts((current) => current.map((row) => (row.id === updated.id ? updated : row)))
    setSelectedAlert((current) => (current?.id === updated.id ? updated : current))
  }, [])

  const resolveAlert = useCallback(async (alert: AlertRecord) => {
    let previous: AlertRecord[] = []
    setAlerts((current) => {
      previous = current
      return current.map((row) => (row.id === alert.id ? { ...row, is_resolved: true } : row))
    })
    try {
      const updated = await api.resolveAlert(alert.id)
      replaceAlert(updated)
      setMessage(`Alert #${alert.id} resolved.`)
    } catch (err) {
      setAlerts(previous)
      setMessage(err instanceof Error ? err.message : "Unable to resolve alert.")
    }
  }, [replaceAlert])

  const acknowledgeAlert = useCallback(async (alert: AlertRecord) => {
    try {
      const updated = await api.acknowledgeAlert(alert.id)
      replaceAlert(updated)
      setMessage(`Alert #${alert.id} acknowledged.`)
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Unable to acknowledge alert.")
    }
  }, [replaceAlert])

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

  const openAssignDialog = useCallback((alert: AlertRecord) => {
    setAssignAlertTarget(alert)
    setSelectedAssignee(alert.assigned_to || "")
    setAssignDialogOpen(true)
    loadAssignableUsers(alert.assigned_to)
  }, [])

  const submitAssignAlert = useCallback(async () => {
    if (!assignAlertTarget || !selectedAssignee) return
    setAssignSaving(true)
    setAssignError("")
    try {
      const updated = await api.assignAlert(assignAlertTarget.id, selectedAssignee)
      replaceAlert(updated)
      setMessage(`Alert #${assignAlertTarget.id} assigned to ${updated.assigned_to || selectedAssignee}.`)
      setAssignDialogOpen(false)
    } catch (err) {
      setAssignError(err instanceof Error ? err.message : "Unable to assign alert.")
    } finally {
      setAssignSaving(false)
    }
  }, [assignAlertTarget, replaceAlert, selectedAssignee])

  const escalateAlert = useCallback(async (alert: AlertRecord) => {
    try {
      const updated = await api.escalateAlert(alert.id)
      replaceAlert(updated)
      setMessage(`Alert #${alert.id} escalated.`)
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Unable to escalate alert.")
    }
  }, [replaceAlert])

  const columns = useMemo<ColumnDef<AlertRecord>[]>(
    () => [
      {
        accessorKey: "id",
        header: ({ column }) => <DataTableColumnHeader column={column} title="ID" />,
      },
      {
        accessorKey: "severity",
        header: ({ column }) => <DataTableColumnHeader column={column} title="Severity" />,
        cell: ({ row }) => <SeverityBadge severity={row.original.severity} />,
      },
      {
        accessorKey: "message",
        header: "Message",
        cell: ({ row }) => <span className="block max-w-xl whitespace-normal">{row.original.message}</span>,
      },
      { accessorKey: "owner_team", header: "Owner Team" },
      { accessorKey: "assigned_to", header: "Assigned To" },
      {
        id: "status",
        header: "Status",
        cell: ({ row }) => <StatusBadge status={alertStatus(row.original)} />,
      },
      {
        accessorKey: "created_at",
        header: ({ column }) => <DataTableColumnHeader column={column} title="Created" />,
        cell: ({ row }) => formatDateTime(row.original.created_at),
      },
      {
        id: "actions",
        header: "Actions",
        cell: ({ row }) =>
          row.original.is_resolved ? null : (
            <Button size="sm" onClick={() => resolveAlert(row.original)}>
              Resolve
            </Button>
          ),
      },
    ],
    [resolveAlert]
  )

  return (
    <AppShell>
      <PageHeader
        eyebrow="Operations"
        title="Alert Operations"
        subtitle="Triage, assign, escalate, and resolve data quality incidents from one operational console."
        onRefresh={loadAlerts}
      />

      {message ? (
        <Card className="rounded-xl border-blue-100 bg-blue-50 shadow-sm">
          <CardContent className="p-4 text-sm text-blue-700">{message}</CardContent>
        </Card>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <EnterpriseMetricCard title="Total Alerts" value={alerts.length} description="All recorded alerts" icon={BellRing} tone="blue" />
        <EnterpriseMetricCard title="Open Alerts" value={openAlerts.length} description="Needs triage" icon={AlertTriangle} tone="amber" />
        <EnterpriseMetricCard title="Critical Alerts" value={criticalAlerts.length} description="High priority" icon={ShieldAlert} tone="red" />
        <EnterpriseMetricCard title="Resolved Alerts" value={resolvedAlerts.length} description="Closed incidents" icon={CheckCircle2} tone="green" />
      </div>

      <AlertFiltersPanel value={filters} onChange={setFilters} />

      <Tabs defaultValue="triage">
        <TabsList className="flex flex-wrap">
          <TabsTrigger value="triage">Triage Board</TabsTrigger>
          <TabsTrigger value="critical">Critical</TabsTrigger>
          <TabsTrigger value="assigned">Assigned to Me</TabsTrigger>
          <TabsTrigger value="sla">SLA Breaches</TabsTrigger>
          <TabsTrigger value="escalated">Escalated</TabsTrigger>
          <TabsTrigger value="resolved">Resolved</TabsTrigger>
          <TabsTrigger value="all">All Alerts</TabsTrigger>
        </TabsList>

        <TabsContent value="triage" className="mt-5">
          <div className="grid gap-6 xl:grid-cols-[1fr_360px]">
            <div className="grid gap-4">
              {openAlerts.slice(0, 8).map((alert) => (
                <div
                  className="cursor-pointer text-left"
                  key={alert.id}
                  role="button"
                  tabIndex={0}
                  onClick={() => setSelectedAlert(alert)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault()
                      setSelectedAlert(alert)
                    }
                  }}
                >
                  <AlertCard
                    alert={alert}
                    onResolve={resolveAlert}
                    onAcknowledge={acknowledgeAlert}
                    onAssign={canAssignAlerts ? openAssignDialog : undefined}
                    onEscalate={escalateAlert}
                  />
                </div>
              ))}
            </div>
            <AlertTimeline alert={selectedAlert ?? openAlerts[0]} />
          </div>
        </TabsContent>

        <TabsContent value="critical" className="mt-5">
          <div className="grid gap-4">
            {criticalAlerts.map((alert) => (
              <AlertCard
                key={alert.id}
                alert={alert}
                onResolve={resolveAlert}
                onAcknowledge={acknowledgeAlert}
                onAssign={canAssignAlerts ? openAssignDialog : undefined}
                onEscalate={escalateAlert}
              />
            ))}
          </div>
        </TabsContent>
        <TabsContent value="assigned" className="mt-5">
          <EnterpriseDataTable columns={columns} data={filteredAlerts.filter((alert) => Boolean(alert.assigned_to))} loading={loading} />
        </TabsContent>
        <TabsContent value="sla" className="mt-5">
          <EnterpriseDataTable columns={columns} data={filteredAlerts.filter((alert) => String(alert.message ?? "").toLowerCase().includes("sla"))} loading={loading} />
        </TabsContent>
        <TabsContent value="escalated" className="mt-5">
          <EnterpriseDataTable columns={columns} data={escalatedAlerts} loading={loading} />
        </TabsContent>
        <TabsContent value="resolved" className="mt-5">
          <EnterpriseDataTable columns={columns} data={resolvedAlerts} loading={loading} />
        </TabsContent>
        <TabsContent value="all" className="mt-5">
          <EnterpriseDataTable columns={columns} data={filteredAlerts} loading={loading} />
        </TabsContent>
      </Tabs>
      <AlertAssignDialog
        alert={assignAlertTarget}
        users={assignUsers}
        open={assignDialogOpen}
        loading={assignUsersLoading}
        saving={assignSaving}
        selectedUsername={selectedAssignee}
        error={assignError}
        onOpenChange={setAssignDialogOpen}
        onSelectedUsernameChange={setSelectedAssignee}
        onAssign={submitAssignAlert}
      />
    </AppShell>
  )
}

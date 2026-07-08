"use client"

import { useEffect, useMemo, useState } from "react"
import type { ColumnDef } from "@tanstack/react-table"
import { Activity, Database, FileCheck2, PlayCircle, RotateCcw, Server, ShieldCheck, Wrench, XCircle } from "lucide-react"

import { EnterpriseDataTable } from "@/components/data-table/data-table"
import { AppShell } from "@/components/app-shell"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { EnterpriseMetricCard } from "@/components/ui-custom/metric-card"
import { PageHeader } from "@/components/ui-custom/page-header"
import { StatusBadge } from "@/components/ui-custom/status-badge"
import { api } from "@/lib/api-client"
import { APP_VERSION, ENVIRONMENT_NAME } from "@/lib/constants"
import { formatDateTime } from "@/lib/formatters"
import type { AuditLog, CleaningJob } from "@/lib/types"

export default function AdminPage() {
  const [apiStatus, setApiStatus] = useState("UNKNOWN")
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([])
  const [cleaningJobs, setCleaningJobs] = useState<CleaningJob[]>([])
  const [message, setMessage] = useState("")
  const [loading, setLoading] = useState(true)

  async function loadAdmin() {
    setLoading(true)
    setMessage("")
    try {
      await api.health()
      setApiStatus("READY")
      const [auditRows, jobRows] = await Promise.all([
        api.auditLogs().catch(() => []),
        api.cleaningJobs().catch(() => []),
      ])
      setAuditLogs(auditRows)
      setCleaningJobs(jobRows)
    } catch (err) {
      setApiStatus("UNREADY")
      setMessage(err instanceof Error ? err.message : "Unable to load admin data.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadAdmin()
  }, [])

  async function runChecksNow() {
    setMessage("Running checks...")
    try {
      const response = await api.runChecks()
      setMessage(response.success ? "Checks completed." : "Checks completed with errors.")
      await loadAdmin()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Unable to run checks.")
    }
  }

  const columns = useMemo<ColumnDef<AuditLog>[]>(
    () => [
      { accessorKey: "created_at", header: "Created", cell: ({ row }) => formatDateTime(row.original.created_at) },
      { accessorKey: "event_type", header: "Event" },
      { accessorKey: "username", header: "User" },
      { accessorKey: "role", header: "Role" },
      { accessorKey: "entity_type", header: "Entity" },
      { accessorKey: "entity_id", header: "Entity ID" },
    ],
    []
  )
  const pendingCleaning = cleaningJobs.filter((job) => job.status === "PENDING_APPROVAL")
  const executedCleaning = cleaningJobs.filter((job) => job.status === "EXECUTED")
  const failedCleaning = cleaningJobs.filter((job) => job.status === "FAILED")
  const rolledBackCleaning = cleaningJobs.filter((job) => job.status === "ROLLED_BACK")

  return (
    <AppShell>
      <PageHeader
        eyebrow="Administration"
        title="Admin Control Center"
        subtitle="System health, API status, configuration posture, and operational maintenance actions."
        onRefresh={loadAdmin}
        actions={<Button onClick={runChecksNow}><PlayCircle className="size-4" /> Run Checks Now</Button>}
      />

      {message ? <Card className="rounded-xl border-blue-100 bg-blue-50"><CardContent className="p-4 text-sm text-blue-700">{message}</CardContent></Card> : null}

      <div className="grid gap-4 md:grid-cols-3 xl:grid-cols-6">
        <EnterpriseMetricCard title="API Status" value={apiStatus} description="FastAPI health" icon={Server} tone={apiStatus === "READY" ? "green" : "red"} />
        <EnterpriseMetricCard title="Database Status" value="Configured" description="Via backend settings" icon={Database} tone="blue" />
        <EnterpriseMetricCard title="Config Status" value="Available" description="Rules and env loaded" icon={FileCheck2} tone="green" />
        <EnterpriseMetricCard title="Environment" value={ENVIRONMENT_NAME} description="Frontend setting" icon={Activity} tone="slate" />
        <EnterpriseMetricCard title="Version" value={APP_VERSION} description="Console version" icon={ShieldCheck} tone="blue" />
        <EnterpriseMetricCard title="Release Audit" value="Ready" description="Run release audit in CLI" icon={FileCheck2} tone="amber" />
      </div>

      <div className="grid gap-6 xl:grid-cols-[420px_1fr]">
        <Card className="rounded-xl shadow-sm">
          <CardHeader>
            <CardTitle>Maintenance Actions</CardTitle>
            <CardDescription>Operational actions are API-protected and audited.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button className="w-full justify-start" variant="outline" onClick={loadAdmin}>Validate Config</Button>
            <Button className="w-full justify-start" variant="outline" onClick={runChecksNow}>Run Checks Now</Button>
            <Button className="w-full justify-start" variant="outline" disabled>Export Latest Report</Button>
            <div className="rounded-xl border bg-slate-50 p-3 text-sm">
              Current API state: <StatusBadge status={apiStatus} />
            </div>
          </CardContent>
        </Card>
        <EnterpriseDataTable columns={columns} data={auditLogs} loading={loading} />
      </div>

      <Card className="rounded-xl shadow-sm">
        <CardHeader>
          <CardTitle>Data Cleaning Activity</CardTitle>
          <CardDescription>Operational remediation job counts and recent cleaning events.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="grid gap-4 md:grid-cols-5">
            <EnterpriseMetricCard title="Cleaning Jobs" value={cleaningJobs.length} description="Total jobs" icon={Wrench} tone="blue" />
            <EnterpriseMetricCard title="Pending Approval" value={pendingCleaning.length} description="Admin review" icon={ShieldCheck} tone="amber" />
            <EnterpriseMetricCard title="Executed" value={executedCleaning.length} description="Applied changes" icon={FileCheck2} tone="green" />
            <EnterpriseMetricCard title="Failed" value={failedCleaning.length} description="Needs review" icon={XCircle} tone="red" />
            <EnterpriseMetricCard title="Rolled Back" value={rolledBackCleaning.length} description="Restored changes" icon={RotateCcw} tone="slate" />
          </div>
          <div className="rounded-xl border bg-slate-50 p-4 text-sm text-slate-600">
            Recent cleaning activity is also searchable in Audit Logs using events such as CLEANING_JOB_CREATED,
            CLEANING_JOB_EXECUTED, CLEANING_JOB_FAILED, and CLEANING_JOB_ROLLED_BACK.
          </div>
        </CardContent>
      </Card>
    </AppShell>
  )
}

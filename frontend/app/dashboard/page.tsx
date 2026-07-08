"use client"

import { useEffect, useMemo, useState } from "react"
import { AlertTriangle, BellRing, Database, Gauge, ListChecks, ShieldCheck } from "lucide-react"

import { FailedChecksChart } from "@/components/charts/failed-checks-chart"
import { QualityTrendChart } from "@/components/charts/quality-trend-chart"
import { SeverityDistributionChart } from "@/components/charts/severity-distribution-chart"
import { AppShell } from "@/components/app-shell"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { EnterpriseMetricCard } from "@/components/ui-custom/metric-card"
import { PageHeader } from "@/components/ui-custom/page-header"
import { SeverityBadge } from "@/components/ui-custom/severity-badge"
import { StatusBadge } from "@/components/ui-custom/status-badge"
import { EmptyState } from "@/components/ui-custom/empty-state"
import { api } from "@/lib/api-client"
import { formatDateTime, formatNumber, formatPercent } from "@/lib/formatters"
import type { AlertRecord, CheckResult, RunSummary, SlaResult } from "@/lib/types"

function countBy<T>(rows: T[], getter: (row: T) => string | undefined) {
  const counts = new Map<string, number>()
  rows.forEach((row) => {
    const key = getter(row) || "Unknown"
    counts.set(key, (counts.get(key) ?? 0) + 1)
  })
  return Array.from(counts.entries()).map(([name, value]) => ({ name, value }))
}

export default function DashboardPage() {
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [latestRun, setLatestRun] = useState<RunSummary | null>(null)
  const [results, setResults] = useState<CheckResult[]>([])
  const [alerts, setAlerts] = useState<AlertRecord[]>([])
  const [sla, setSla] = useState<SlaResult[]>([])
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState("")
  const [lastRefreshed, setLastRefreshed] = useState("")

  async function loadDashboard() {
    setLoading(true)
    setMessage("")
    try {
      const [runRows, latest, alertRows, slaRows] = await Promise.all([
        api.runs(),
        api.latestRun().catch(() => null),
        api.alerts(false).catch(() => []),
        api.sla().catch(() => []),
      ])
      setRuns(runRows)
      setLatestRun(latest)
      setAlerts(alertRows)
      setSla(slaRows)
      setResults(latest?.run_id ? await api.results(latest.run_id).catch(() => []) : [])
      setLastRefreshed(formatDateTime(new Date()))
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Unable to load dashboard data.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadDashboard()
  }, [])

  const datasets = new Set(results.map((row) => row.dataset_name).filter(Boolean))
  const failedResults = results.filter((row) => row.status === "FAIL")
  const criticalResults = results.filter((row) => row.severity === "CRITICAL")
  const slaPassCount = sla.filter((row) => row.sla_status === "PASS").length
  const slaCompliance = sla.length ? (slaPassCount / sla.length) * 100 : 0

  const trendData = [...runs]
    .reverse()
    .map((run) => ({ run_id: run.run_id, quality_score: Number(run.quality_score ?? 0) }))

  const failedByDataset = useMemo(() => {
    const counts = new Map<string, number>()
    failedResults.forEach((row) => {
      const dataset = row.dataset_name ?? "Unknown"
      counts.set(dataset, (counts.get(dataset) ?? 0) + 1)
    })
    return Array.from(counts.entries()).map(([dataset, failed]) => ({ dataset, failed }))
  }, [failedResults])

  const degradedDatasets = failedByDataset.slice(0, 5)
  const alertsBySeverity = countBy(alerts, (row) => row.severity)
  const slaDistribution = countBy(sla, (row) => row.sla_status)

  async function runChecks() {
    setMessage("Running checks...")
    try {
      const response = await api.runChecks()
      setMessage(response.success ? "Checks completed successfully." : "Checks completed with errors.")
      await loadDashboard()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Unable to run checks.")
    }
  }

  return (
    <AppShell>
      <PageHeader
        eyebrow="Command Center"
        title="Executive Dashboard"
        subtitle="Management-ready view of quality score, SLA posture, open alerts, and datasets requiring action."
        onRefresh={loadDashboard}
        actions={<Button onClick={runChecks}>Run Checks Now</Button>}
      />

      {message ? (
        <Card className="rounded-xl border-blue-100 bg-blue-50 shadow-sm">
          <CardContent className="p-4 text-sm text-blue-700">{message}</CardContent>
        </Card>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
        <EnterpriseMetricCard
          title="Quality Score"
          value={loading ? "..." : formatPercent(latestRun?.quality_score, 2)}
          description="Latest weighted score"
          icon={Gauge}
          tone="blue"
        />
        <EnterpriseMetricCard
          title="SLA Compliance"
          value={loading ? "..." : formatPercent(slaCompliance, 1)}
          description={`${slaPassCount} of ${sla.length} passing`}
          icon={ShieldCheck}
          tone="green"
        />
        <EnterpriseMetricCard title="Open Alerts" value={alerts.length} description="Unresolved" icon={BellRing} tone="amber" />
        <EnterpriseMetricCard title="Critical Issues" value={criticalResults.length} description="Highest priority" icon={AlertTriangle} tone="red" />
        <EnterpriseMetricCard title="Datasets Monitored" value={datasets.size} description="In latest run" icon={Database} tone="slate" />
        <EnterpriseMetricCard
          title="Latest Run Status"
          value={latestRun?.overall_status ?? "-"}
          description={latestRun?.run_time ? formatDateTime(latestRun.run_time) : "No run"}
          icon={ListChecks}
          tone={latestRun?.overall_status === "PASS" ? "green" : "red"}
        />
      </div>

      <Card className="rounded-xl shadow-sm">
        <CardHeader>
          <CardTitle>Executive Summary</CardTitle>
          <CardDescription>Last refreshed {lastRefreshed || "not yet"}</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          <div className="rounded-xl border bg-slate-50 p-4">
            <div className="text-sm font-medium text-slate-500">Latest Run</div>
            <div className="mt-2 text-xl font-semibold">#{latestRun?.run_id ?? "-"}</div>
            <div className="mt-2"><StatusBadge status={latestRun?.overall_status} /></div>
          </div>
          <div className="rounded-xl border bg-slate-50 p-4">
            <div className="text-sm font-medium text-slate-500">Check Volume</div>
            <div className="mt-2 text-xl font-semibold">{formatNumber(latestRun?.total_checks ?? 0)}</div>
            <p className="mt-1 text-sm text-slate-500">{formatNumber(latestRun?.failed_checks ?? 0)} failed checks</p>
          </div>
          <div className="rounded-xl border bg-slate-50 p-4">
            <div className="text-sm font-medium text-slate-500">Operational Posture</div>
            <div className="mt-2 text-xl font-semibold">{alerts.length ? "Action Required" : "Stable"}</div>
            <p className="mt-1 text-sm text-slate-500">{alerts.length} open alerts in queue</p>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-2">
        <QualityTrendChart data={trendData} />
        <FailedChecksChart data={failedByDataset} />
        <SeverityDistributionChart data={alertsBySeverity} />
        <SeverityDistributionChart data={slaDistribution} title="SLA Status Distribution" description="Dataset SLA outcomes." />
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <Card className="rounded-xl shadow-sm">
          <CardHeader>
            <CardTitle>Recently Degraded Datasets</CardTitle>
            <CardDescription>Datasets with failed checks in the latest run.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {degradedDatasets.length ? degradedDatasets.map((row) => (
              <div className="flex items-center justify-between rounded-xl border p-3" key={row.dataset}>
                <span className="font-medium">{row.dataset}</span>
                <span className="text-sm text-red-600">{row.failed} failures</span>
              </div>
            )) : <EmptyState title="No degraded datasets" description="The latest run has no dataset-level failures." />}
          </CardContent>
        </Card>

        <Card className="rounded-xl shadow-sm">
          <CardHeader>
            <CardTitle>Critical Issues Requiring Action</CardTitle>
            <CardDescription>Highest severity quality failures.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {criticalResults.slice(0, 5).map((row, index) => (
              <div className="rounded-xl border p-3" key={`${row.id}-${index}`}>
                <div className="flex items-center justify-between gap-3">
                  <span className="font-medium">{row.dataset_name}</span>
                  <SeverityBadge severity={row.severity} />
                </div>
                <p className="mt-1 text-sm text-slate-500">{row.check_type} on {row.column_name ?? row.column ?? "table"}</p>
              </div>
            ))}
            {!criticalResults.length ? <EmptyState title="No critical issues" description="Critical severity failures will appear here." /> : null}
          </CardContent>
        </Card>

        <Card className="rounded-xl shadow-sm">
          <CardHeader>
            <CardTitle>Latest Open Alerts</CardTitle>
            <CardDescription>Operational follow-up queue.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {alerts.slice(0, 5).map((alert) => (
              <div className="rounded-xl border p-3" key={alert.id}>
                <div className="flex items-center justify-between gap-3">
                  <span className="font-medium">Alert #{alert.id}</span>
                  <SeverityBadge severity={alert.severity} />
                </div>
                <p className="mt-1 line-clamp-2 text-sm text-slate-500">{alert.message}</p>
              </div>
            ))}
            {!alerts.length ? <EmptyState title="No open alerts" description="Unresolved alerts will appear here." /> : null}
          </CardContent>
        </Card>
      </div>
    </AppShell>
  )
}


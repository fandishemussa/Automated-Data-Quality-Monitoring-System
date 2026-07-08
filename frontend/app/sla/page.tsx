"use client"

import { useEffect, useMemo, useState } from "react"
import type { ColumnDef } from "@tanstack/react-table"
import { AlertTriangle, BellRing, Gauge, ShieldCheck, Target } from "lucide-react"

import { FailedChecksChart } from "@/components/charts/failed-checks-chart"
import { SeverityDistributionChart } from "@/components/charts/severity-distribution-chart"
import { SlaTrendChart } from "@/components/charts/sla-trend-chart"
import { DataTableColumnHeader } from "@/components/data-table/data-table-column-header"
import { EnterpriseDataTable } from "@/components/data-table/data-table"
import { AppShell } from "@/components/app-shell"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { EnterpriseMetricCard } from "@/components/ui-custom/metric-card"
import { PageHeader } from "@/components/ui-custom/page-header"
import { StatusBadge } from "@/components/ui-custom/status-badge"
import { api } from "@/lib/api-client"
import { formatNumber, formatPercent } from "@/lib/formatters"
import type { AlertRecord, SlaResult } from "@/lib/types"

function countByDataset(rows: SlaResult[]) {
  const counts = new Map<string, number>()
  rows.forEach((row) => counts.set(row.dataset_name ?? "Unknown", (counts.get(row.dataset_name ?? "Unknown") ?? 0) + 1))
  return Array.from(counts.entries()).map(([dataset, failed]) => ({ dataset, failed }))
}

export default function SlaPage() {
  const [rows, setRows] = useState<SlaResult[]>([])
  const [alerts, setAlerts] = useState<AlertRecord[]>([])
  const [selectedDataset, setSelectedDataset] = useState("")
  const [message, setMessage] = useState("")
  const [loading, setLoading] = useState(true)

  async function loadData() {
    setLoading(true)
    setMessage("")
    try {
      const [slaRows, alertRows] = await Promise.all([api.sla(), api.alerts(false).catch(() => [])])
      setRows(slaRows)
      setAlerts(alertRows)
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Unable to load SLA data.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const breachedRows = rows.filter((row) => row.sla_status !== "PASS")
  const compliance = rows.length ? ((rows.length - breachedRows.length) / rows.length) * 100 : 0
  const averageScore = rows.length
    ? rows.reduce((total, row) => total + Number(row.actual_quality_score ?? 0), 0) / rows.length
    : 0
  const atRiskRows = rows.filter((row) => row.sla_status === "WARN" || Number(row.actual_quality_score ?? 0) < Number(row.minimum_quality_score ?? 0) + 2)
  const openSlaAlerts = alerts.filter((alert) => String(alert.message ?? "").toLowerCase().includes("sla"))

  const trendData = useMemo(() => {
    const grouped = new Map<number, SlaResult[]>()
    rows.forEach((row) => {
      if (!row.run_id) return
      grouped.set(row.run_id, [...(grouped.get(row.run_id) ?? []), row])
    })
    return Array.from(grouped.entries()).map(([run_id, runRows]) => ({
      run_id,
      compliance: runRows.length ? (runRows.filter((row) => row.sla_status === "PASS").length / runRows.length) * 100 : 0,
    }))
  }, [rows])

  const statusDistribution = useMemo(() => {
    const counts = new Map<string, number>()
    rows.forEach((row) => counts.set(row.sla_status ?? "Unknown", (counts.get(row.sla_status ?? "Unknown") ?? 0) + 1))
    return Array.from(counts.entries()).map(([name, value]) => ({ name, value }))
  }, [rows])

  const columns = useMemo<ColumnDef<SlaResult>[]>(
    () => [
      { accessorKey: "dataset_name", header: "Dataset" },
      { accessorKey: "minimum_quality_score", header: "Minimum Score", cell: ({ row }) => formatPercent(row.original.minimum_quality_score) },
      { accessorKey: "actual_quality_score", header: ({ column }) => <DataTableColumnHeader column={column} title="Actual Score" />, cell: ({ row }) => formatPercent(row.original.actual_quality_score) },
      { accessorKey: "actual_failed_checks", header: "Failed Checks" },
      { accessorKey: "actual_critical_issues", header: "Critical Issues" },
      { accessorKey: "sla_status", header: "SLA Status", cell: ({ row }) => <StatusBadge status={row.original.sla_status} /> },
      { id: "owner", header: "Owner Team", cell: ({ row }) => row.original.dataset_name ? "Data Governance" : "-" },
      { id: "action", header: "Recommended Action", cell: ({ row }) => row.original.sla_status === "PASS" ? "Monitor" : "Review failed checks and owner handoff" },
    ],
    []
  )

  const selected = rows.find((row) => row.dataset_name === selectedDataset) ?? rows[0]

  return (
    <AppShell>
      <PageHeader
        eyebrow="Governance"
        title="SLA Command Center"
        subtitle="Track dataset-level data quality commitments, breaches, and recommended governance actions."
        onRefresh={loadData}
      />

      {message ? <Card className="rounded-xl border-blue-100 bg-blue-50"><CardContent className="p-4 text-sm text-blue-700">{message}</CardContent></Card> : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <EnterpriseMetricCard title="SLA Compliance" value={formatPercent(compliance)} description="Datasets passing SLA" icon={ShieldCheck} tone="green" />
        <EnterpriseMetricCard title="Breached Datasets" value={breachedRows.length} description="Needs governance action" icon={AlertTriangle} tone="red" />
        <EnterpriseMetricCard title="At-Risk Datasets" value={atRiskRows.length} description="Near threshold" icon={Target} tone="amber" />
        <EnterpriseMetricCard title="Average Quality Score" value={formatPercent(averageScore)} description="Across SLA rows" icon={Gauge} tone="blue" />
        <EnterpriseMetricCard title="Open SLA Alerts" value={openSlaAlerts.length} description="Unresolved" icon={BellRing} tone="slate" />
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <div className="xl:col-span-2"><SlaTrendChart data={trendData} /></div>
        <SeverityDistributionChart data={statusDistribution} title="SLA Status Distribution" description="Pass, fail, and warning status mix." />
      </div>
      <FailedChecksChart data={countByDataset(breachedRows)} />

      <div className="grid gap-6 xl:grid-cols-[1fr_360px]">
        <EnterpriseDataTable columns={columns} data={rows} loading={loading} />
        <Card className="rounded-xl shadow-sm">
          <CardHeader>
            <CardTitle>Dataset Drill-Down</CardTitle>
            <CardDescription>Select a dataset row to inspect SLA posture.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <select className="w-full rounded-lg border px-3 py-2 text-sm" value={selected?.dataset_name ?? ""} onChange={(event) => setSelectedDataset(event.target.value)}>
              {Array.from(new Set(rows.map((row) => row.dataset_name).filter(Boolean))).map((dataset) => (
                <option key={dataset} value={dataset}>{dataset}</option>
              ))}
            </select>
            {selected ? (
              <div className="space-y-3 rounded-xl border bg-slate-50 p-4 text-sm">
                <div className="flex items-center justify-between"><span>Status</span><StatusBadge status={selected.sla_status} /></div>
                <div className="flex items-center justify-between"><span>Actual score</span><strong>{formatPercent(selected.actual_quality_score)}</strong></div>
                <div className="flex items-center justify-between"><span>Failed checks</span><strong>{formatNumber(selected.actual_failed_checks)}</strong></div>
                <p className="text-slate-500">{selected.reason || "No SLA reason recorded."}</p>
              </div>
            ) : null}
          </CardContent>
        </Card>
      </div>
    </AppShell>
  )
}


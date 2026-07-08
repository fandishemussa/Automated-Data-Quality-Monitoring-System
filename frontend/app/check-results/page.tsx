"use client"

import { useEffect, useMemo, useState } from "react"
import type { ColumnDef } from "@tanstack/react-table"
import { AlertTriangle, CheckCircle2, ListChecks, XCircle } from "lucide-react"

import { AppShell } from "@/components/app-shell"
import { DataTableColumnHeader } from "@/components/data-table/data-table-column-header"
import { EnterpriseDataTable } from "@/components/data-table/data-table"
import { Card, CardContent } from "@/components/ui/card"
import { EnterpriseMetricCard } from "@/components/ui-custom/metric-card"
import { PageHeader } from "@/components/ui-custom/page-header"
import { SeverityBadge } from "@/components/ui-custom/severity-badge"
import { StatusBadge } from "@/components/ui-custom/status-badge"
import { api } from "@/lib/api-client"
import { formatPercent } from "@/lib/formatters"
import type { CheckResult } from "@/lib/types"

export default function CheckResultsPage() {
  const [rows, setRows] = useState<CheckResult[]>([])
  const [message, setMessage] = useState("")
  const [loading, setLoading] = useState(true)

  async function loadRows() {
    setLoading(true)
    setMessage("")
    try {
      setRows(await api.results())
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Unable to load check results.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadRows()
  }, [])

  const passed = rows.filter((row) => row.status === "PASS").length
  const failed = rows.filter((row) => row.status === "FAIL").length
  const critical = rows.filter((row) => row.severity === "CRITICAL").length

  const columns = useMemo<ColumnDef<CheckResult>[]>(
    () => [
      { accessorKey: "run_id", header: ({ column }) => <DataTableColumnHeader column={column} title="Run" /> },
      { accessorKey: "dataset_name", header: "Dataset" },
      { accessorKey: "check_type", header: "Check Type" },
      { accessorKey: "column_name", header: "Column" },
      { accessorKey: "status", header: "Status", cell: ({ row }) => <StatusBadge status={row.original.status} /> },
      { accessorKey: "severity", header: "Severity", cell: ({ row }) => <SeverityBadge severity={row.original.severity} /> },
      { accessorKey: "failed_rows", header: ({ column }) => <DataTableColumnHeader column={column} title="Failed Rows" /> },
      { accessorKey: "failure_rate", header: "Failure Rate", cell: ({ row }) => formatPercent(row.original.failure_rate) },
    ],
    []
  )

  return (
    <AppShell>
      <PageHeader
        eyebrow="Monitoring"
        title="Check Results"
        subtitle="All persisted data quality check outcomes with sorting, search, pagination, and export."
        onRefresh={loadRows}
      />
      {message ? <Card className="rounded-xl border-blue-100 bg-blue-50"><CardContent className="p-4 text-sm text-blue-700">{message}</CardContent></Card> : null}
      <div className="grid gap-4 md:grid-cols-4">
        <EnterpriseMetricCard title="Total Results" value={rows.length} description="Persisted checks" icon={ListChecks} tone="blue" />
        <EnterpriseMetricCard title="Passed" value={passed} description="Healthy checks" icon={CheckCircle2} tone="green" />
        <EnterpriseMetricCard title="Failed" value={failed} description="Needs review" icon={XCircle} tone="red" />
        <EnterpriseMetricCard title="Critical" value={critical} description="Highest severity" icon={AlertTriangle} tone="amber" />
      </div>
      <EnterpriseDataTable columns={columns} data={rows} loading={loading} />
    </AppShell>
  )
}


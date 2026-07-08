"use client"

import { useEffect, useMemo, useState } from "react"
import type { ColumnDef } from "@tanstack/react-table"
import { AlertTriangle, Columns3, GitCompareArrows } from "lucide-react"

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

export default function SchemaDriftPage() {
  const [rows, setRows] = useState<CheckResult[]>([])
  const [message, setMessage] = useState("")
  const [loading, setLoading] = useState(true)

  async function loadRows() {
    setLoading(true)
    setMessage("")
    try {
      const allResults = await api.results()
      setRows(allResults.filter((row) => String(row.check_type ?? "").toLowerCase().includes("schema")))
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Unable to load schema drift checks.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadRows()
  }, [])

  const failed = rows.filter((row) => row.status === "FAIL")
  const columns = useMemo<ColumnDef<CheckResult>[]>(
    () => [
      { accessorKey: "run_id", header: ({ column }) => <DataTableColumnHeader column={column} title="Run" /> },
      { accessorKey: "dataset_name", header: "Dataset" },
      { accessorKey: "column_name", header: "Column" },
      { accessorKey: "rule", header: "Rule", cell: ({ row }) => <span className="block max-w-xl whitespace-normal">{row.original.rule}</span> },
      { accessorKey: "status", header: "Status", cell: ({ row }) => <StatusBadge status={row.original.status} /> },
      { accessorKey: "severity", header: "Severity", cell: ({ row }) => <SeverityBadge severity={row.original.severity} /> },
      { accessorKey: "failure_rate", header: "Failure Rate", cell: ({ row }) => formatPercent(row.original.failure_rate) },
    ],
    []
  )

  return (
    <AppShell>
      <PageHeader
        eyebrow="Governance"
        title="Schema Drift"
        subtitle="Monitor added, removed, reordered, or changed source-table columns detected by schema drift checks."
        onRefresh={loadRows}
      />
      {message ? <Card className="rounded-xl border-blue-100 bg-blue-50"><CardContent className="p-4 text-sm text-blue-700">{message}</CardContent></Card> : null}
      <div className="grid gap-4 md:grid-cols-3">
        <EnterpriseMetricCard title="Schema Checks" value={rows.length} description="Detected in results" icon={Columns3} tone="blue" />
        <EnterpriseMetricCard title="Drift Failures" value={failed.length} description="Requires review" icon={AlertTriangle} tone="red" />
        <EnterpriseMetricCard title="Datasets Checked" value={new Set(rows.map((row) => row.dataset_name).filter(Boolean)).size} description="Schema monitored" icon={GitCompareArrows} tone="green" />
      </div>
      <EnterpriseDataTable columns={columns} data={rows} loading={loading} emptyTitle="No schema drift records" emptyDescription="Run schema drift checks to populate this view." />
    </AppShell>
  )
}


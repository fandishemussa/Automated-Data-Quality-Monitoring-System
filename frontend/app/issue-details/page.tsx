"use client"

import { useEffect, useMemo, useState } from "react"
import type { ColumnDef } from "@tanstack/react-table"
import { Database, FileWarning, SearchCheck } from "lucide-react"

import { AppShell } from "@/components/app-shell"
import { EnterpriseDataTable } from "@/components/data-table/data-table"
import { Card, CardContent } from "@/components/ui/card"
import { EnterpriseMetricCard } from "@/components/ui-custom/metric-card"
import { PageHeader } from "@/components/ui-custom/page-header"
import { api } from "@/lib/api-client"
import { formatDateTime } from "@/lib/formatters"
import type { IssueDetail, RunSummary } from "@/lib/types"

export default function IssueDetailsPage() {
  const [latestRun, setLatestRun] = useState<RunSummary | null>(null)
  const [rows, setRows] = useState<IssueDetail[]>([])
  const [message, setMessage] = useState("")
  const [loading, setLoading] = useState(true)

  async function loadRows() {
    setLoading(true)
    setMessage("")
    try {
      const run = await api.latestRun()
      setLatestRun(run)
      setRows(await api.issues(run.run_id))
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Unable to load issue details.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadRows()
  }, [])

  const datasets = new Set(rows.map((row) => row.dataset_name).filter(Boolean))
  const columns = useMemo<ColumnDef<IssueDetail>[]>(
    () => [
      { accessorKey: "dataset_name", header: "Dataset" },
      { accessorKey: "check_type", header: "Check Type" },
      { accessorKey: "column_name", header: "Column" },
      { accessorKey: "row_identifier", header: "Row Identifier" },
      { accessorKey: "bad_value", header: "Bad Value" },
      { accessorKey: "reason", header: "Reason", cell: ({ row }) => <span className="block max-w-xl whitespace-normal">{row.original.reason}</span> },
      { accessorKey: "created_at", header: "Created", cell: ({ row }) => formatDateTime(row.original.created_at) },
    ],
    []
  )

  return (
    <AppShell>
      <PageHeader
        eyebrow="Monitoring"
        title="Issue Details"
        subtitle="Failed-row examples and root-cause context for the latest monitoring run."
        onRefresh={loadRows}
      />
      {message ? <Card className="rounded-xl border-blue-100 bg-blue-50"><CardContent className="p-4 text-sm text-blue-700">{message}</CardContent></Card> : null}
      <div className="grid gap-4 md:grid-cols-3">
        <EnterpriseMetricCard title="Latest Run" value={latestRun?.run_id ?? "-"} description="Issue sample source" icon={SearchCheck} tone="blue" />
        <EnterpriseMetricCard title="Issue Examples" value={rows.length} description="Stored failed-row details" icon={FileWarning} tone="red" />
        <EnterpriseMetricCard title="Datasets Impacted" value={datasets.size} description="With issue examples" icon={Database} tone="amber" />
      </div>
      <EnterpriseDataTable columns={columns} data={rows} loading={loading} />
    </AppShell>
  )
}


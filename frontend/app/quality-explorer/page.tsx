"use client"

import { useEffect, useMemo, useState } from "react"
import type { ColumnDef } from "@tanstack/react-table"
import { AlertTriangle, Database, FileWarning, SearchCheck } from "lucide-react"

import { DataTableColumnHeader } from "@/components/data-table/data-table-column-header"
import { EnterpriseDataTable } from "@/components/data-table/data-table"
import { AppShell } from "@/components/app-shell"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { EnterpriseMetricCard } from "@/components/ui-custom/metric-card"
import { PageHeader } from "@/components/ui-custom/page-header"
import { SeverityBadge } from "@/components/ui-custom/severity-badge"
import { StatusBadge } from "@/components/ui-custom/status-badge"
import { api } from "@/lib/api-client"
import { formatNumber, formatPercent } from "@/lib/formatters"
import type { CheckResult, ProfileResult } from "@/lib/types"

export default function QualityExplorerPage() {
  const [results, setResults] = useState<CheckResult[]>([])
  const [profiles, setProfiles] = useState<ProfileResult[]>([])
  const [filters, setFilters] = useState({ dataset: "ALL", status: "ALL", severity: "ALL", checkType: "ALL" })
  const [message, setMessage] = useState("")
  const [loading, setLoading] = useState(true)

  async function loadData() {
    setLoading(true)
    setMessage("")
    try {
      const [resultRows, profileRows] = await Promise.all([
        api.results().catch(() => []),
        api.profiling().catch(() => []),
      ])
      setResults(resultRows)
      setProfiles(profileRows)
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Unable to load quality explorer data.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const datasets = Array.from(new Set(results.map((row) => row.dataset_name).filter(Boolean))) as string[]
  const checkTypes = Array.from(new Set(results.map((row) => row.check_type).filter(Boolean))) as string[]

  const filteredResults = results.filter((row) =>
    (filters.dataset === "ALL" || row.dataset_name === filters.dataset) &&
    (filters.status === "ALL" || row.status === filters.status) &&
    (filters.severity === "ALL" || row.severity === filters.severity) &&
    (filters.checkType === "ALL" || row.check_type === filters.checkType)
  )
  const failedResults = filteredResults.filter((row) => row.status === "FAIL")
  const selectedDataset = filters.dataset !== "ALL" ? filters.dataset : datasets[0]
  const selectedProfiles = profiles.filter((row) => row.dataset_name === selectedDataset)

  const datasetHealth = useMemo(() => datasets.map((dataset) => {
    const rows = results.filter((row) => row.dataset_name === dataset)
    const failed = rows.filter((row) => row.status === "FAIL").length
    const score = rows.length ? ((rows.length - failed) / rows.length) * 100 : 0
    return { dataset, checks: rows.length, failed, score }
  }), [datasets, results])

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
        eyebrow="Investigation"
        title="Quality Explorer"
        subtitle="Drill from dataset health into check type, column, severity, and issue patterns."
        onRefresh={loadData}
      />

      {message ? <Card className="rounded-xl border-blue-100 bg-blue-50"><CardContent className="p-4 text-sm text-blue-700">{message}</CardContent></Card> : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <EnterpriseMetricCard title="Datasets" value={datasets.length} description="Monitored datasets" icon={Database} tone="blue" />
        <EnterpriseMetricCard title="Total Checks" value={filteredResults.length} description="Current filtered view" icon={SearchCheck} tone="slate" />
        <EnterpriseMetricCard title="Failed Checks" value={failedResults.length} description="Needs investigation" icon={AlertTriangle} tone="red" />
        <EnterpriseMetricCard title="Profile Columns" value={selectedProfiles.length} description={selectedDataset ?? "No dataset"} icon={FileWarning} tone="green" />
      </div>

      <div className="grid gap-3 rounded-xl border bg-white p-4 shadow-sm md:grid-cols-4">
        <select className="rounded-lg border px-3 py-2 text-sm" value={filters.dataset} onChange={(event) => setFilters({ ...filters, dataset: event.target.value })}>
          <option value="ALL">All datasets</option>
          {datasets.map((dataset) => <option key={dataset} value={dataset}>{dataset}</option>)}
        </select>
        <select className="rounded-lg border px-3 py-2 text-sm" value={filters.checkType} onChange={(event) => setFilters({ ...filters, checkType: event.target.value })}>
          <option value="ALL">All check types</option>
          {checkTypes.map((checkType) => <option key={checkType} value={checkType}>{checkType}</option>)}
        </select>
        <select className="rounded-lg border px-3 py-2 text-sm" value={filters.status} onChange={(event) => setFilters({ ...filters, status: event.target.value })}>
          <option value="ALL">All statuses</option>
          <option value="PASS">Pass</option>
          <option value="FAIL">Fail</option>
          <option value="SKIPPED">Skipped</option>
        </select>
        <select className="rounded-lg border px-3 py-2 text-sm" value={filters.severity} onChange={(event) => setFilters({ ...filters, severity: event.target.value })}>
          <option value="ALL">All severity</option>
          <option value="CRITICAL">Critical</option>
          <option value="HIGH">High</option>
          <option value="MEDIUM">Medium</option>
          <option value="LOW">Low</option>
        </select>
      </div>

      <Tabs defaultValue="results">
        <TabsList>
          <TabsTrigger value="health">Dataset Health</TabsTrigger>
          <TabsTrigger value="results">Results</TabsTrigger>
          <TabsTrigger value="failed">Failed Checks</TabsTrigger>
          <TabsTrigger value="profiles">Column Profiles</TabsTrigger>
          <TabsTrigger value="raw">View Raw Data</TabsTrigger>
        </TabsList>
        <TabsContent value="health" className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {datasetHealth.map((row) => (
            <Card className="rounded-xl shadow-sm" key={row.dataset}>
              <CardHeader>
                <CardTitle>{row.dataset}</CardTitle>
                <CardDescription>{formatNumber(row.checks)} checks</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-semibold">{formatPercent(row.score)}</div>
                <p className="mt-1 text-sm text-slate-500">{row.failed} failed checks</p>
              </CardContent>
            </Card>
          ))}
        </TabsContent>
        <TabsContent value="results" className="mt-5">
          <EnterpriseDataTable columns={columns} data={filteredResults} loading={loading} />
        </TabsContent>
        <TabsContent value="failed" className="mt-5">
          <EnterpriseDataTable columns={columns} data={failedResults} loading={loading} />
        </TabsContent>
        <TabsContent value="profiles" className="mt-5">
          <Card className="rounded-xl shadow-sm">
            <CardHeader>
              <CardTitle>Column Profile Summary</CardTitle>
              <CardDescription>Profiling API results for {selectedDataset ?? "the selected dataset"}.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3 md:grid-cols-3">
              {selectedProfiles.slice(0, 9).map((profile) => (
                <div className="rounded-xl border bg-slate-50 p-4" key={`${profile.dataset_name}-${profile.column_name}`}>
                  <div className="font-medium">{profile.column_name}</div>
                  <p className="text-sm text-slate-500">{profile.data_type}</p>
                  <div className="mt-3 text-sm">Null rate: {formatPercent(profile.null_rate)}</div>
                  <div className="text-sm">Unique: {formatNumber(profile.unique_count)}</div>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="raw" className="mt-5">
          <pre className="max-h-[520px] overflow-auto rounded-xl border bg-slate-950 p-4 text-xs text-slate-100">
            {JSON.stringify(filteredResults.slice(0, 50), null, 2)}
          </pre>
        </TabsContent>
      </Tabs>
    </AppShell>
  )
}


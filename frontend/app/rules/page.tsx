"use client"

import { useEffect, useMemo, useState } from "react"
import type { ColumnDef } from "@tanstack/react-table"
import { AlertTriangle, Columns3, Database, SlidersHorizontal } from "lucide-react"

import { EnterpriseDataTable } from "@/components/data-table/data-table"
import { AppShell } from "@/components/app-shell"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { EnterpriseMetricCard } from "@/components/ui-custom/metric-card"
import { PageHeader } from "@/components/ui-custom/page-header"
import { SeverityBadge } from "@/components/ui-custom/severity-badge"
import { api } from "@/lib/api-client"
import type { RuleCatalogRow } from "@/lib/types"

export default function RulesPage() {
  const [rows, setRows] = useState<RuleCatalogRow[]>([])
  const [query, setQuery] = useState("")
  const [dataset, setDataset] = useState("ALL")
  const [ruleType, setRuleType] = useState("ALL")
  const [message, setMessage] = useState("")
  const [loading, setLoading] = useState(true)

  async function loadRules() {
    setLoading(true)
    setMessage("")
    try {
      setRows(await api.rules())
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Unable to load rules.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadRules()
  }, [])

  const datasets = Array.from(new Set(rows.map((row) => row.dataset_name).filter(Boolean))) as string[]
  const ruleTypes = Array.from(new Set(rows.map((row) => row.rule_type).filter(Boolean))) as string[]
  const filteredRows = rows.filter((row) =>
    (dataset === "ALL" || row.dataset_name === dataset) &&
    (ruleType === "ALL" || row.rule_type === ruleType) &&
    (!query || JSON.stringify(row).toLowerCase().includes(query.toLowerCase()))
  )

  const coverageWarnings = rows.filter((row) => {
    const config = String(row.rule_config ?? "").toLowerCase()
    return config.includes("missing") || config.includes("invalid") || config.includes("threshold")
  })

  const columns = useMemo<ColumnDef<RuleCatalogRow>[]>(
    () => [
      { accessorKey: "dataset_name", header: "Dataset" },
      { accessorKey: "rule_type", header: "Rule Type" },
      { accessorKey: "column_name", header: "Column" },
      { accessorKey: "severity", header: "Severity", cell: ({ row }) => <SeverityBadge severity={row.original.severity} /> },
      { accessorKey: "enabled", header: "Enabled", cell: ({ row }) => String(row.original.enabled ?? true) },
      {
        accessorKey: "rule_config",
        header: "Rule Config",
        cell: ({ row }) => (
          <code className="block max-w-xl whitespace-normal rounded-lg bg-slate-100 px-2 py-1 text-xs">
            {row.original.rule_config}
          </code>
        ),
      },
    ],
    []
  )

  return (
    <AppShell>
      <PageHeader
        eyebrow="Governance"
        title="Rules Studio"
        subtitle="Inspect active YAML rules, coverage, dataset scope, and rule configurations from the UI."
        onRefresh={loadRules}
      />

      {message ? <Card className="rounded-xl border-blue-100 bg-blue-50"><CardContent className="p-4 text-sm text-blue-700">{message}</CardContent></Card> : null}

      <div className="grid gap-4 md:grid-cols-4">
        <EnterpriseMetricCard title="Total Rules" value={rows.length} description="Flattened YAML rules" icon={SlidersHorizontal} tone="blue" />
        <EnterpriseMetricCard title="Datasets Covered" value={datasets.length} description="Dataset-level coverage" icon={Database} tone="green" />
        <EnterpriseMetricCard title="Rule Types" value={ruleTypes.length} description="Distinct checks" icon={Columns3} tone="slate" />
        <EnterpriseMetricCard title="Coverage Warnings" value={coverageWarnings.length} description="Potential config issues" icon={AlertTriangle} tone="amber" />
      </div>

      <div className="grid gap-3 rounded-xl border bg-white p-4 shadow-sm md:grid-cols-3">
        <input className="rounded-lg border px-3 py-2 text-sm" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search rules" />
        <select className="rounded-lg border px-3 py-2 text-sm" value={dataset} onChange={(event) => setDataset(event.target.value)}>
          <option value="ALL">All datasets</option>
          {datasets.map((item) => <option key={item} value={item}>{item}</option>)}
        </select>
        <select className="rounded-lg border px-3 py-2 text-sm" value={ruleType} onChange={(event) => setRuleType(event.target.value)}>
          <option value="ALL">All rule types</option>
          {ruleTypes.map((item) => <option key={item} value={item}>{item}</option>)}
        </select>
      </div>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Rules Overview</TabsTrigger>
          <TabsTrigger value="dataset">Dataset Rules</TabsTrigger>
          <TabsTrigger value="column">Column Rules</TabsTrigger>
          <TabsTrigger value="global">Global Rules</TabsTrigger>
          <TabsTrigger value="raw">Raw YAML</TabsTrigger>
        </TabsList>
        <TabsContent value="overview" className="mt-5">
          <EnterpriseDataTable columns={columns} data={filteredRows} loading={loading} />
        </TabsContent>
        <TabsContent value="dataset" className="mt-5">
          <EnterpriseDataTable columns={columns} data={filteredRows.filter((row) => row.dataset_name && !row.column_name)} loading={loading} />
        </TabsContent>
        <TabsContent value="column" className="mt-5">
          <EnterpriseDataTable columns={columns} data={filteredRows.filter((row) => row.column_name)} loading={loading} />
        </TabsContent>
        <TabsContent value="global" className="mt-5">
          <EnterpriseDataTable columns={columns} data={filteredRows.filter((row) => row.dataset_name === "global_rules")} loading={loading} />
        </TabsContent>
        <TabsContent value="raw" className="mt-5">
          <Card className="rounded-xl shadow-sm">
            <CardHeader>
              <CardTitle>Raw Rules Payload</CardTitle>
              <CardDescription>Rule editing and approval workflow is planned for Enterprise edition.</CardDescription>
            </CardHeader>
            <CardContent>
              <pre className="max-h-[560px] overflow-auto rounded-xl bg-slate-950 p-4 text-xs text-slate-100">
                {JSON.stringify(rows, null, 2)}
              </pre>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </AppShell>
  )
}


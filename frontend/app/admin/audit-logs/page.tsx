"use client"

import { useEffect, useMemo, useState } from "react"
import type { ColumnDef } from "@tanstack/react-table"

import { EnterpriseDataTable } from "@/components/data-table/data-table"
import { AppShell } from "@/components/app-shell"
import { Card, CardContent } from "@/components/ui/card"
import { PageHeader } from "@/components/ui-custom/page-header"
import { api } from "@/lib/api-client"
import { formatDateTime } from "@/lib/formatters"
import type { AuditLog } from "@/lib/types"

export default function AuditLogsPage() {
  const [rows, setRows] = useState<AuditLog[]>([])
  const [message, setMessage] = useState("")
  const [loading, setLoading] = useState(true)

  async function loadRows() {
    setLoading(true)
    setMessage("")
    try {
      setRows(await api.auditLogs())
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Unable to load audit logs.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadRows()
  }, [])

  const columns = useMemo<ColumnDef<AuditLog>[]>(
    () => [
      { accessorKey: "created_at", header: "Created Time", cell: ({ row }) => formatDateTime(row.original.created_at) },
      { accessorKey: "event_type", header: "Event Type" },
      { accessorKey: "username", header: "User" },
      { accessorKey: "role", header: "Role" },
      { accessorKey: "entity_type", header: "Entity" },
      { accessorKey: "entity_id", header: "Entity ID" },
    ],
    []
  )

  return (
    <AppShell>
      <PageHeader eyebrow="Administration" title="Audit Logs" subtitle="Trace operational actions across dashboard and API users." onRefresh={loadRows} />
      {message ? <Card className="rounded-xl border-blue-100 bg-blue-50"><CardContent className="p-4 text-sm text-blue-700">{message}</CardContent></Card> : null}
      <EnterpriseDataTable columns={columns} data={rows} loading={loading} />
    </AppShell>
  )
}


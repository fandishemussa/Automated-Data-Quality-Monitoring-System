import { Clock, UserRound } from "lucide-react"

import { AlertActions } from "@/components/alerts/alert-actions"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { SeverityBadge } from "@/components/ui-custom/severity-badge"
import { StatusBadge } from "@/components/ui-custom/status-badge"
import { formatDateTime } from "@/lib/formatters"
import type { AlertRecord } from "@/lib/types"

type AlertCardProps = {
  alert: AlertRecord
  onResolve: (alert: AlertRecord) => Promise<void> | void
  onAcknowledge?: (alert: AlertRecord) => Promise<void> | void
  onAssign?: (alert: AlertRecord) => Promise<void> | void
  onEscalate?: (alert: AlertRecord) => Promise<void> | void
}

export function AlertCard({ alert, onResolve, onAcknowledge, onAssign, onEscalate }: AlertCardProps) {
  const status = alert.is_resolved ? "RESOLVED" : alert.escalation_status || "OPEN"

  return (
    <Card className="rounded-xl shadow-sm">
      <CardHeader className="gap-3">
        <div className="flex items-start justify-between gap-4">
          <div>
            <CardTitle className="text-base">Alert #{alert.id}</CardTitle>
            <p className="mt-1 text-sm text-slate-500">{alert.alert_type ?? "Data quality alert"}</p>
          </div>
          <div className="flex flex-wrap justify-end gap-2">
            <SeverityBadge severity={alert.severity} />
            <StatusBadge status={status} />
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm leading-6 text-slate-700">{alert.message}</p>
        <div className="grid gap-3 text-sm text-slate-500 md:grid-cols-3">
          <div className="flex items-center gap-2">
            <UserRound className="size-4" />
            {alert.owner_team || "Unassigned team"}
          </div>
          <div>{alert.assigned_to || "No assignee"}</div>
          <div className="flex items-center gap-2">
            <Clock className="size-4" />
            {formatDateTime(alert.created_at)}
          </div>
        </div>
        <AlertActions
          alert={alert}
          onResolve={onResolve}
          onAcknowledge={onAcknowledge}
          onAssign={onAssign}
          onEscalate={onEscalate}
        />
      </CardContent>
    </Card>
  )
}

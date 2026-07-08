import { CircleDot } from "lucide-react"

import { formatDateTime } from "@/lib/formatters"
import type { AlertRecord } from "@/lib/types"

export function AlertTimeline({ alert }: { alert?: AlertRecord }) {
  if (!alert) return null

  const items = [
    { label: "Created", time: alert.created_at },
    alert.escalated_at ? { label: "Escalated", time: alert.escalated_at } : null,
    alert.resolved_at ? { label: "Resolved", time: alert.resolved_at } : null,
  ].filter(Boolean) as { label: string; time?: string }[]

  return (
    <div className="rounded-xl border bg-white p-4 shadow-sm">
      <div className="font-semibold">Alert Timeline</div>
      <div className="mt-4 space-y-3">
        {items.map((item) => (
          <div className="flex gap-3 text-sm" key={item.label}>
            <CircleDot className="mt-0.5 size-4 text-blue-600" />
            <div>
              <div className="font-medium text-slate-900">{item.label}</div>
              <div className="text-slate-500">{formatDateTime(item.time)}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}


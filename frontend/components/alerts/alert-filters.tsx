"use client"

import { Input } from "@/components/ui/input"

export type AlertFilters = {
  search: string
  severity: string
  status: string
  ownerTeam: string
  assignedTo: string
}

type AlertFiltersProps = {
  value: AlertFilters
  onChange: (value: AlertFilters) => void
}

export function AlertFiltersPanel({ value, onChange }: AlertFiltersProps) {
  function update(key: keyof AlertFilters, nextValue: string) {
    onChange({ ...value, [key]: nextValue })
  }

  return (
    <div className="grid gap-3 rounded-xl border bg-white p-4 shadow-sm md:grid-cols-5">
      <Input value={value.search} onChange={(event) => update("search", event.target.value)} placeholder="Search alerts" />
      <select className="rounded-lg border bg-white px-3 text-sm" value={value.severity} onChange={(event) => update("severity", event.target.value)}>
        <option value="ALL">All severity</option>
        <option value="CRITICAL">Critical</option>
        <option value="HIGH">High</option>
        <option value="MEDIUM">Medium</option>
        <option value="LOW">Low</option>
      </select>
      <select className="rounded-lg border bg-white px-3 text-sm" value={value.status} onChange={(event) => update("status", event.target.value)}>
        <option value="ALL">All statuses</option>
        <option value="OPEN">Open</option>
        <option value="RESOLVED">Resolved</option>
        <option value="ESCALATED">Escalated</option>
      </select>
      <Input value={value.ownerTeam} onChange={(event) => update("ownerTeam", event.target.value)} placeholder="Owner team" />
      <Input value={value.assignedTo} onChange={(event) => update("assignedTo", event.target.value)} placeholder="Assigned to" />
    </div>
  )
}


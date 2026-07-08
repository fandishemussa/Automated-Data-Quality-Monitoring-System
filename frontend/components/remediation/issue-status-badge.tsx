import { StatusBadge } from "@/components/ui-custom/status-badge"

export function IssueStatusBadge({ status }: { status?: string | null }) {
  return <StatusBadge status={status || "OPEN"} />
}


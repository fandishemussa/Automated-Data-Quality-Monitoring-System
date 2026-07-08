import { StatusBadge } from "@/components/ui-custom/status-badge"

export function JobStatusBadge({ status }: { status?: string | null }) {
  return <StatusBadge status={status} />
}


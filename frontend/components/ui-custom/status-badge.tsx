import { Badge } from "@/components/ui/badge"
import { getStatusTone } from "@/lib/theme"
import { cn } from "@/lib/utils"
import { formatStatus } from "@/lib/formatters"

type StatusBadgeProps = {
  status?: string | null
  className?: string
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const tone = getStatusTone(status ?? undefined)
  return (
    <Badge
      variant="outline"
      className={cn(
        "border px-2.5 py-1 font-medium",
        tone === "success" && "border-green-200 bg-green-50 text-green-700",
        tone === "warning" && "border-amber-200 bg-amber-50 text-amber-700",
        tone === "danger" && "border-red-200 bg-red-50 text-red-700",
        tone === "info" && "border-blue-200 bg-blue-50 text-blue-700",
        tone === "neutral" && "border-slate-200 bg-slate-50 text-slate-700",
        className
      )}
    >
      {formatStatus(status)}
    </Badge>
  )
}


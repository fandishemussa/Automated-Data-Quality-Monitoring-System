import { Badge } from "@/components/ui/badge"
import { formatSeverity } from "@/lib/formatters"
import { getSeverityTone } from "@/lib/theme"
import { cn } from "@/lib/utils"

type SeverityBadgeProps = {
  severity?: string | null
  className?: string
}

export function SeverityBadge({ severity, className }: SeverityBadgeProps) {
  const tone = getSeverityTone(severity ?? undefined)
  return (
    <Badge
      variant="outline"
      className={cn(
        "border px-2.5 py-1 font-medium",
        tone === "danger" && "border-red-200 bg-red-50 text-red-700",
        tone === "warning" && "border-amber-200 bg-amber-50 text-amber-700",
        tone === "info" && "border-blue-200 bg-blue-50 text-blue-700",
        tone === "neutral" && "border-slate-200 bg-slate-50 text-slate-700",
        className
      )}
    >
      {formatSeverity(severity)}
    </Badge>
  )
}


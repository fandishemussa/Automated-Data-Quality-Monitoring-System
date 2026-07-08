import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

export function RiskBadge({ risk }: { risk?: string }) {
  const normalized = String(risk || "LOW").toUpperCase()
  return (
    <Badge
      variant="outline"
      className={cn(
        "border px-2.5 py-1 font-medium",
        normalized === "LOW" && "border-green-200 bg-green-50 text-green-700",
        normalized === "MEDIUM" && "border-amber-200 bg-amber-50 text-amber-700",
        normalized === "HIGH" && "border-red-200 bg-red-50 text-red-700"
      )}
    >
      {normalized}
    </Badge>
  )
}


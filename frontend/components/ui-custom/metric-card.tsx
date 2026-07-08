import type { LucideIcon } from "lucide-react"

import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"

type EnterpriseMetricCardProps = {
  title: string
  value: string | number
  description?: string
  icon?: LucideIcon
  tone?: "blue" | "green" | "amber" | "red" | "slate"
}

const toneClasses = {
  blue: "bg-blue-50 text-blue-700 ring-blue-100",
  green: "bg-green-50 text-green-700 ring-green-100",
  amber: "bg-amber-50 text-amber-700 ring-amber-100",
  red: "bg-red-50 text-red-700 ring-red-100",
  slate: "bg-slate-50 text-slate-700 ring-slate-100",
}

export function EnterpriseMetricCard({
  title,
  value,
  description,
  icon: Icon,
  tone = "blue",
}: EnterpriseMetricCardProps) {
  return (
    <Card className="rounded-xl border-slate-200 shadow-sm">
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</p>
            <div className="mt-3 text-2xl font-semibold tracking-tight text-slate-950">{value}</div>
            {description ? <p className="mt-1 text-sm text-slate-500">{description}</p> : null}
          </div>
          {Icon ? (
            <div className={cn("rounded-lg p-2 ring-1", toneClasses[tone])}>
              <Icon className="size-5" />
            </div>
          ) : null}
        </div>
      </CardContent>
    </Card>
  )
}


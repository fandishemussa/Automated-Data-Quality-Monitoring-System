import type { LucideIcon } from "lucide-react"
import { Database } from "lucide-react"

import { Button } from "@/components/ui/button"

type EmptyStateProps = {
  title: string
  description?: string
  actionLabel?: string
  onAction?: () => void
  icon?: LucideIcon
}

export function EmptyState({
  title,
  description,
  actionLabel,
  onAction,
  icon: Icon = Database,
}: EmptyStateProps) {
  return (
    <div className="flex min-h-48 flex-col items-center justify-center rounded-xl border border-dashed bg-slate-50/70 p-8 text-center">
      <div className="rounded-xl bg-white p-3 text-slate-500 shadow-sm ring-1 ring-slate-200">
        <Icon className="size-6" />
      </div>
      <h3 className="mt-4 text-base font-semibold text-slate-950">{title}</h3>
      {description ? <p className="mt-1 max-w-md text-sm text-slate-500">{description}</p> : null}
      {actionLabel && onAction ? (
        <Button className="mt-4" variant="outline" onClick={onAction}>
          {actionLabel}
        </Button>
      ) : null}
    </div>
  )
}


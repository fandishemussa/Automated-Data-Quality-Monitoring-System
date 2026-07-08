import type { ReactNode } from "react"

import { Button } from "@/components/ui/button"

type PageHeaderProps = {
  title: string
  subtitle?: string
  eyebrow?: string
  actions?: ReactNode
  onRefresh?: () => void
}

export function PageHeader({ title, subtitle, eyebrow, actions, onRefresh }: PageHeaderProps) {
  return (
    <div className="flex flex-col justify-between gap-4 rounded-xl border bg-card p-5 shadow-sm lg:flex-row lg:items-center">
      <div>
        {eyebrow ? <div className="text-xs font-semibold uppercase tracking-wide text-blue-600">{eyebrow}</div> : null}
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-950">{title}</h1>
        {subtitle ? <p className="mt-1 max-w-3xl text-sm text-slate-500">{subtitle}</p> : null}
      </div>
      <div className="flex items-center gap-2">
        {onRefresh ? (
          <Button variant="outline" onClick={onRefresh}>
            Refresh
          </Button>
        ) : null}
        {actions}
      </div>
    </div>
  )
}


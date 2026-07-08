"use client"

import { CheckCircle2, Forward, UserPlus } from "lucide-react"
import type { MouseEvent } from "react"

import { Button } from "@/components/ui/button"
import type { AlertRecord } from "@/lib/types"

type AlertActionsProps = {
  alert: AlertRecord
  onResolve: (alert: AlertRecord) => Promise<void> | void
  onAcknowledge?: (alert: AlertRecord) => Promise<void> | void
  onAssign?: (alert: AlertRecord) => Promise<void> | void
  onEscalate?: (alert: AlertRecord) => Promise<void> | void
}

export function AlertActions({ alert, onResolve, onAcknowledge, onAssign, onEscalate }: AlertActionsProps) {
  if (alert.is_resolved) return null

  function runAction(event: MouseEvent<HTMLButtonElement>, action: () => Promise<void> | void) {
    event.preventDefault()
    event.stopPropagation()
    action()
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Button
        variant="outline"
        size="sm"
        onClick={(event) => runAction(event, () => onAcknowledge?.(alert))}
        title="Acknowledge alert"
      >
        <CheckCircle2 className="size-4" />
        Acknowledge
      </Button>
      {onAssign ? (
        <Button variant="outline" size="sm" title="Assign alert" onClick={(event) => runAction(event, () => onAssign(alert))}>
          <UserPlus className="size-4" />
          Assign
        </Button>
      ) : null}
      <Button variant="outline" size="sm" onClick={(event) => runAction(event, () => onEscalate?.(alert))} title="Escalate alert">
        <Forward className="size-4" />
        Escalate
      </Button>
      <Button
        size="sm"
        onClick={(event) => runAction(event, () => {
          const needsConfirm = alert.severity === "CRITICAL" || alert.severity === "HIGH"
          if (needsConfirm && !window.confirm(`Resolve ${alert.severity} alert #${alert.id}?`)) return
          onResolve(alert)
        })}
      >
        Resolve
      </Button>
    </div>
  )
}

import { Wrench } from "lucide-react"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { RiskBadge } from "@/components/remediation/risk-badge"
import type { CleaningSuggestion } from "@/lib/types"

type CleaningActionCardProps = {
  suggestion: CleaningSuggestion
  selected?: boolean
  onSelect?: (suggestion: CleaningSuggestion) => void
}

export function CleaningActionCard({ suggestion, selected, onSelect }: CleaningActionCardProps) {
  return (
    <button className="text-left" onClick={() => onSelect?.(suggestion)}>
      <Card className={`rounded-xl shadow-sm transition ${selected ? "border-blue-500 ring-2 ring-blue-100" : ""}`}>
        <CardHeader>
          <CardTitle className="flex items-center justify-between gap-3 text-base">
            <span className="flex items-center gap-2">
              <Wrench className="size-4 text-blue-600" />
              {suggestion.action}
            </span>
            <RiskBadge risk={suggestion.risk} />
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-slate-600">{suggestion.description}</CardContent>
      </Card>
    </button>
  )
}


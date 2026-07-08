import { BarChart3 } from "lucide-react"

export function EmptyChart({ message = "No chart data available." }: { message?: string }) {
  return (
    <div className="flex h-full min-h-64 flex-col items-center justify-center rounded-xl border border-dashed bg-slate-50 text-center text-sm text-slate-500">
      <BarChart3 className="mb-2 size-7 text-slate-400" />
      {message}
    </div>
  )
}


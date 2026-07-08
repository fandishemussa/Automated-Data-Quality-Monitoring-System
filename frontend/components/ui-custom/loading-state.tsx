import { Skeleton } from "@/components/ui/skeleton"

type LoadingStateProps = {
  rows?: number
}

export function LoadingState({ rows = 4 }: LoadingStateProps) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }).map((_, index) => (
        <Skeleton key={index} className="h-16 rounded-xl" />
      ))}
    </div>
  )
}


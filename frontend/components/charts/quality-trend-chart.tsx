"use client"

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

import { EmptyChart } from "@/components/charts/empty-chart"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

type TrendPoint = { run_id?: number | string; quality_score?: number }

export function QualityTrendChart({ data }: { data: TrendPoint[] }) {
  if (!data.length) return <EmptyChart message="Run checks to populate the quality trend." />

  return (
    <Card className="rounded-xl shadow-sm">
      <CardHeader>
        <CardTitle>Quality Score Trend</CardTitle>
        <CardDescription>Recent monitoring runs and score movement.</CardDescription>
      </CardHeader>
      <CardContent className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="run_id" tickLine={false} axisLine={false} />
            <YAxis domain={[0, 100]} tickLine={false} axisLine={false} />
            <Tooltip />
            <Line type="monotone" dataKey="quality_score" stroke="#2563eb" strokeWidth={3} dot={{ r: 3 }} />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}


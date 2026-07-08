"use client"

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

import { EmptyChart } from "@/components/charts/empty-chart"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

type FailedPoint = { dataset: string; failed: number }

export function FailedChecksChart({ data }: { data: FailedPoint[] }) {
  if (!data.length) return <EmptyChart message="No failed checks found for this view." />

  return (
    <Card className="rounded-xl shadow-sm">
      <CardHeader>
        <CardTitle>Failed Checks by Dataset</CardTitle>
        <CardDescription>Datasets contributing most to quality failures.</CardDescription>
      </CardHeader>
      <CardContent className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="dataset" tickLine={false} axisLine={false} />
            <YAxis allowDecimals={false} tickLine={false} axisLine={false} />
            <Tooltip />
            <Bar dataKey="failed" fill="#dc2626" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}


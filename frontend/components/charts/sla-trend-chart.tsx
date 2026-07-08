"use client"

import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

import { EmptyChart } from "@/components/charts/empty-chart"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

type SlaPoint = { run_id?: number | string; compliance?: number }

export function SlaTrendChart({ data }: { data: SlaPoint[] }) {
  if (!data.length) return <EmptyChart message="No SLA trend available yet." />

  return (
    <Card className="rounded-xl shadow-sm">
      <CardHeader>
        <CardTitle>SLA Compliance Trend</CardTitle>
        <CardDescription>Percentage of datasets meeting SLA by run.</CardDescription>
      </CardHeader>
      <CardContent className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <defs>
              <linearGradient id="slaCompliance" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#16a34a" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#16a34a" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="run_id" tickLine={false} axisLine={false} />
            <YAxis domain={[0, 100]} tickLine={false} axisLine={false} />
            <Tooltip />
            <Area type="monotone" dataKey="compliance" stroke="#16a34a" fill="url(#slaCompliance)" strokeWidth={3} />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}


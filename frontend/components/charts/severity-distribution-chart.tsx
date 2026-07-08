"use client"

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts"

import { EmptyChart } from "@/components/charts/empty-chart"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

const colors = ["#dc2626", "#d97706", "#2563eb", "#64748b", "#16a34a"]

type SeverityPoint = { name: string; value: number }

export function SeverityDistributionChart({
  data,
  title = "Alerts by Severity",
  description = "Current severity distribution.",
}: {
  data: SeverityPoint[]
  title?: string
  description?: string
}) {
  if (!data.length) return <EmptyChart message="No severity data available." />

  return (
    <Card className="rounded-xl shadow-sm">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" innerRadius={58} outerRadius={92} paddingAngle={3}>
              {data.map((entry, index) => (
                <Cell key={entry.name} fill={colors[index % colors.length]} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}


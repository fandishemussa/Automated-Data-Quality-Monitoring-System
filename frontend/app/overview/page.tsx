"use client"

import Link from "next/link"
import { Activity, AlertTriangle, BarChart3, ShieldCheck } from "lucide-react"

import { AppShell } from "@/components/app-shell"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { PageHeader } from "@/components/ui-custom/page-header"

const actions = [
  { href: "/dashboard", title: "Executive Dashboard", description: "Management-ready KPIs and trends.", icon: BarChart3 },
  { href: "/quality-explorer", title: "Quality Explorer", description: "Investigate checks, datasets, columns, and profiles.", icon: Activity },
  { href: "/alerts", title: "Alert Operations", description: "Triage ownership, severity, and alert resolution.", icon: AlertTriangle },
  { href: "/sla", title: "SLA Command Center", description: "Track dataset-level governance commitments.", icon: ShieldCheck },
]

export default function OverviewPage() {
  return (
    <AppShell>
      <PageHeader
        eyebrow="Command Center"
        title="Overview"
        subtitle="Navigate the core operational workspaces in the Data Quality Command Center."
      />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {actions.map((action) => {
          const Icon = action.icon
          return (
            <Card className="rounded-xl shadow-sm" key={action.href}>
              <CardHeader>
                <div className="mb-3 flex size-10 items-center justify-center rounded-xl bg-blue-50 text-blue-700">
                  <Icon className="size-5" />
                </div>
                <CardTitle>{action.title}</CardTitle>
                <CardDescription>{action.description}</CardDescription>
              </CardHeader>
              <CardContent>
                <Link
                  href={action.href}
                  className="inline-flex h-8 items-center justify-center rounded-lg border px-3 text-sm font-medium transition hover:bg-slate-50"
                >
                  Open
                </Link>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </AppShell>
  )
}

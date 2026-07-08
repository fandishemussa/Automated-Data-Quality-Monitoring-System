"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { ChevronRight } from "lucide-react"

const labels: Record<string, string> = {
  dashboard: "Executive Dashboard",
  profile: "My Profile",
  overview: "Overview",
  "check-results": "Check Results",
  "issue-details": "Issue Details",
  remediation: "Data Remediation Center",
  alerts: "Alerts",
  "quality-explorer": "Quality Explorer",
  sla: "SLA",
  "schema-drift": "Schema Drift",
  lineage: "Lineage",
  rules: "Rules",
  profiling: "Profiling",
  admin: "Admin",
  setup: "Setup",
  notifications: "Notifications",
  users: "User Management",
  "audit-logs": "Audit Logs",
}

export function Breadcrumbs() {
  const pathname = usePathname()
  const parts = pathname.split("/").filter(Boolean)

  return (
    <div className="flex items-center gap-1 text-xs text-slate-500">
      <Link href="/dashboard" className="hover:text-slate-900">
        Home
      </Link>
      {parts.map((part, index) => {
        const href = `/${parts.slice(0, index + 1).join("/")}`
        return (
          <div className="flex items-center gap-1" key={href}>
            <ChevronRight className="size-3" />
            <Link href={href} className="hover:text-slate-900">
              {labels[part] ?? part}
            </Link>
          </div>
        )
      })}
    </div>
  )
}

"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  Activity,
  BarChart3,
  BellRing,
  Columns3,
  FileWarning,
  GitBranch,
  LayoutDashboard,
  ListChecks,
  ScrollText,
  SearchCheck,
  Send,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  Wrench,
  Target,
  UsersRound,
} from "lucide-react"

import { cn } from "@/lib/utils"
import { getStoredUserRole } from "@/lib/api-client"

const groups = [
  {
    label: "Command Center",
    items: [
      { href: "/dashboard", label: "Executive Dashboard", icon: LayoutDashboard },
      { href: "/overview", label: "Overview", icon: BarChart3 },
    ],
  },
  {
    label: "Operations",
    items: [
      { href: "/remediation", label: "Data Remediation Center", icon: Wrench },
      { href: "/alerts", label: "Alert Operations", icon: BellRing },
    ],
  },
  {
    label: "Monitoring",
    items: [
      { href: "/quality-explorer", label: "Quality Explorer", icon: SearchCheck },
      { href: "/check-results", label: "Check Results", icon: ListChecks },
      { href: "/issue-details", label: "Issue Details", icon: FileWarning },
    ],
  },
  {
    label: "Governance",
    items: [
      { href: "/sla", label: "SLA Command Center", icon: Target },
      { href: "/lineage", label: "Data Lineage", icon: GitBranch },
      { href: "/rules", label: "Rules Studio", icon: SlidersHorizontal },
      { href: "/profiling", label: "Data Profiling", icon: Activity },
      { href: "/schema-drift", label: "Schema Drift", icon: Columns3 },
    ],
  },
  {
    label: "Administration",
    adminOnly: true,
    items: [
      { href: "/admin/notifications", label: "Notification Center", icon: Send },
      { href: "/admin/users", label: "User Management", icon: UsersRound },
      { href: "/admin/audit-logs", label: "Audit Logs", icon: ScrollText },
      { href: "/admin/setup", label: "Setup Wizard", icon: Settings },
      { href: "/admin", label: "Admin Control Center", icon: ShieldCheck },
    ],
  },
]

export function Sidebar() {
  const pathname = usePathname()
  const role = getStoredUserRole()
  const visibleGroups = groups
    .map((group) => ({
      ...group,
      items: group.adminOnly && role !== "admin" ? [] : group.items,
    }))
    .filter((group) => group.items.length > 0)

  return (
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-76 border-r border-slate-800 bg-slate-950 text-slate-100 lg:flex lg:flex-col">
      <div className="flex h-16 items-center gap-3 border-b border-slate-800 px-5">
        <div className="flex size-10 items-center justify-center rounded-xl bg-blue-600 text-sm font-bold text-white shadow-soft">
          DQ
        </div>
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold">Data Quality Command</div>
          <div className="text-xs text-slate-400">Enterprise Console</div>
        </div>
      </div>
      <nav className="flex-1 overflow-y-auto px-3 py-4">
        {visibleGroups.map((group) => (
          <div className="mb-5" key={group.label}>
            <div className="px-3 pb-2 text-[0.68rem] font-semibold uppercase tracking-[0.16em] text-slate-500">
              {group.label}
            </div>
            <div className="space-y-1">
              {group.items.map((item) => {
                const Icon = item.icon
                const active = pathname === item.href
                return (
                  <Link
                    key={`${group.label}-${item.label}`}
                    href={item.href}
                    className={cn(
                      "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-slate-300 transition hover:bg-slate-900 hover:text-white",
                      active && "bg-blue-600 text-white shadow-soft hover:bg-blue-600"
                    )}
                  >
                    <Icon className="size-4" />
                    <span className="truncate">{item.label}</span>
                  </Link>
                )
              })}
            </div>
          </div>
        ))}
      </nav>
      <div className="border-t border-slate-800 p-4">
        <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-3 text-xs text-slate-400">
          API-protected SaaS console for data quality operations, governance, and incident triage.
        </div>
      </div>
    </aside>
  )
}

"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  Activity,
  AlertTriangle,
  ClipboardList,
  Database,
  GitBranch,
  LayoutDashboard,
  LockKeyhole,
  ScrollText,
  ShieldCheck,
} from "lucide-react"

import { cn } from "@/lib/utils"

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/alerts", label: "Alerts", icon: AlertTriangle },
  { href: "/quality-explorer", label: "Quality Explorer", icon: Activity },
  { href: "/sla", label: "SLA", icon: ShieldCheck },
  { href: "/lineage", label: "Lineage", icon: GitBranch },
  { href: "/rules", label: "Rules", icon: ClipboardList },
  { href: "/profiling", label: "Profiling", icon: Database },
  { href: "/admin", label: "Admin", icon: LockKeyhole },
]

export function SidebarNav() {
  const pathname = usePathname()

  return (
    <aside className="hidden w-72 shrink-0 border-r bg-muted/20 md:block">
      <div className="flex h-16 items-center gap-3 border-b px-6">
        <div className="flex size-9 items-center justify-center rounded-lg bg-primary text-sm font-semibold text-primary-foreground">
          DQ
        </div>
        <div>
          <div className="font-semibold">Quality Command</div>
          <div className="text-xs text-muted-foreground">Enterprise Console</div>
        </div>
      </div>
      <nav className="space-y-1 p-4">
        {navItems.map((item) => {
          const Icon = item.icon
          const active = pathname === item.href
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground transition hover:bg-muted hover:text-foreground",
                active && "bg-primary text-primary-foreground hover:bg-primary hover:text-primary-foreground"
              )}
            >
              <Icon className="size-4" />
              {item.label}
            </Link>
          )
        })}
      </nav>
      <div className="mx-4 mt-6 rounded-lg border bg-background p-3 text-xs text-muted-foreground">
        <ScrollText className="mb-2 size-4" />
        Streamlit remains available for the legacy dashboard while this SaaS console evolves.
      </div>
    </aside>
  )
}


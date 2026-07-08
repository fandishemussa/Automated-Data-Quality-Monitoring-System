"use client"

import { usePathname, useRouter } from "next/navigation"
import { LogOut, ShieldCheck } from "lucide-react"

import { Button } from "@/components/ui/button"
import { clearStoredApiToken } from "@/lib/api-client"

const titles: Record<string, string> = {
  "/dashboard": "Executive Dashboard",
  "/alerts": "Alerts",
  "/quality-explorer": "Quality Explorer",
  "/sla": "SLA Tracking",
  "/lineage": "Data Lineage",
  "/rules": "Rules Catalog",
  "/profiling": "Data Profiling",
  "/admin": "Administration",
}

export function Header() {
  const pathname = usePathname()
  const router = useRouter()
  const title = titles[pathname] ?? "Data Quality Platform"

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b bg-background/95 px-6 backdrop-blur">
      <div>
        <div className="text-sm text-muted-foreground">Automated Data Quality Monitoring</div>
        <h1 className="text-lg font-semibold">{title}</h1>
      </div>
      <div className="flex items-center gap-3">
        <div className="hidden items-center gap-2 rounded-lg border px-3 py-1.5 text-xs text-muted-foreground sm:flex">
          <ShieldCheck className="size-3.5" />
          API key session
        </div>
        <Button
          variant="outline"
          onClick={() => {
            clearStoredApiToken()
            router.push("/login")
          }}
        >
          <LogOut />
          Logout
        </Button>
      </div>
    </header>
  )
}


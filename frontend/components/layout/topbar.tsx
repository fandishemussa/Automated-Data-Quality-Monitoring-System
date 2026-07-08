"use client"

import { RefreshCw } from "lucide-react"

import { Breadcrumbs } from "@/components/layout/breadcrumbs"
import { UserMenu } from "@/components/layout/user-menu"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { APP_VERSION, ENVIRONMENT_NAME } from "@/lib/constants"

export function Topbar() {
  return (
    <header className="sticky top-0 z-20 flex min-h-16 items-center justify-between gap-4 border-b bg-white/90 px-4 backdrop-blur lg:px-8">
      <div className="min-w-0">
        <Breadcrumbs />
        <div className="mt-1 flex items-center gap-2">
          <Badge variant="outline" className="border-blue-200 bg-blue-50 text-blue-700">
            {ENVIRONMENT_NAME}
          </Badge>
          <Badge variant="outline" className="border-slate-200 bg-slate-50 text-slate-600">
            {APP_VERSION}
          </Badge>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <Button variant="outline" onClick={() => window.location.reload()} aria-label="Refresh page">
          <RefreshCw className="size-4" />
          <span className="hidden sm:inline">Refresh</span>
        </Button>
        <UserMenu />
      </div>
    </header>
  )
}


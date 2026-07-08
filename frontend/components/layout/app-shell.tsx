"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"

import { Sidebar } from "@/components/layout/sidebar"
import { Topbar } from "@/components/layout/topbar"
import { getStoredApiToken } from "@/lib/api-client"

export function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const [ready, setReady] = useState(false)

  useEffect(() => {
    if (!getStoredApiToken()) {
      router.replace("/login")
      return
    }
    setReady(true)
  }, [router])

  if (!ready) {
    return <div className="min-h-screen bg-slate-50" />
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <Sidebar />
      <div className="min-h-screen lg:pl-76">
        <Topbar />
        <main className="mx-auto w-full max-w-[1600px] space-y-6 p-4 lg:p-8">{children}</main>
      </div>
    </div>
  )
}


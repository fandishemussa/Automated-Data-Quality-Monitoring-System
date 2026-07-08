"use client"

import { useRouter } from "next/navigation"
import { LogOut, UserRound } from "lucide-react"

import { Button } from "@/components/ui/button"
import { clearStoredApiToken, getStoredUserName, getStoredUserRole } from "@/lib/api-client"

export function UserMenu() {
  const router = useRouter()
  const username = getStoredUserName()
  const role = getStoredUserRole()

  return (
    <div className="flex items-center gap-2 rounded-xl border bg-white px-2 py-1.5 shadow-sm">
      <div className="flex size-8 items-center justify-center rounded-lg bg-slate-100 text-slate-600">
        <UserRound className="size-4" />
      </div>
      <div className="hidden text-left md:block">
        <div className="text-xs font-medium text-slate-900">{username}</div>
        <div className="text-[0.68rem] capitalize text-slate-500">{role} session</div>
      </div>
      <Button
        size="icon-sm"
        variant="ghost"
        aria-label="Open profile"
        onClick={() => {
          router.push("/profile")
        }}
      >
        <UserRound className="size-4" />
      </Button>
      <Button
        size="icon-sm"
        variant="ghost"
        aria-label="Logout"
        onClick={() => {
          clearStoredApiToken()
          router.push("/login")
        }}
      >
        <LogOut className="size-4" />
      </Button>
    </div>
  )
}

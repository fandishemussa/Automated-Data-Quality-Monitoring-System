"use client"

import { FormEvent, useState } from "react"
import { useRouter } from "next/navigation"
import { Database, KeyRound, ShieldCheck, UserRound } from "lucide-react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { api, clearStoredApiToken, getApiBaseUrl, setStoredUserSession } from "@/lib/api-client"

export default function LoginPage() {
  const router = useRouter()
  const [username, setUsername] = useState(process.env.NEXT_PUBLIC_USER_NAME ?? "admin")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoading(true)
    setError("")

    try {
      const response = await api.login({ username, password })
      setStoredUserSession(response.token, response.user)
      router.push("/dashboard")
    } catch (err) {
      clearStoredApiToken()
      setError(err instanceof Error ? err.message : "Login failed. Check your username and password.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-950">
      <div className="grid min-h-screen lg:grid-cols-[1fr_0.82fr]">
        <section className="hidden flex-col justify-between bg-slate-950 p-10 text-white lg:flex">
          <div className="flex items-center gap-3">
            <div className="flex size-11 items-center justify-center rounded-xl bg-blue-600 font-bold shadow-soft">
              DQ
            </div>
            <div>
              <div className="font-semibold">Data Quality Command Center</div>
              <div className="text-sm text-slate-400">Enterprise monitoring portal</div>
            </div>
          </div>
          <div className="max-w-xl">
            <div className="mb-4 inline-flex rounded-full border border-blue-400/30 bg-blue-400/10 px-3 py-1 text-sm text-blue-100">
              Secure enterprise data quality monitoring portal
            </div>
            <h1 className="text-4xl font-semibold tracking-tight">
              Govern data quality, alerts, lineage, and SLA health from one command surface.
            </h1>
            <p className="mt-4 text-base leading-7 text-slate-300">
              Built for operational teams that need reliable checks, ownership, auditability, and executive visibility.
            </p>
          </div>
          <div className="grid gap-3 text-sm text-slate-300">
            {[
              { icon: ShieldCheck, label: "Secure access" },
              { icon: Database, label: "Role-based dashboard" },
              { icon: KeyRound, label: "API protected" },
            ].map((item) => {
              const Icon = item.icon
              return (
                <div className="flex items-center gap-3" key={item.label}>
                  <div className="rounded-lg bg-white/10 p-2 text-blue-100">
                    <Icon className="size-4" />
                  </div>
                  {item.label}
                </div>
              )
            })}
          </div>
        </section>

        <section className="flex items-center justify-center bg-slate-50 p-6">
          <Card className="w-full max-w-md rounded-2xl border-slate-200 shadow-soft">
            <CardHeader className="space-y-4">
              <div className="flex size-12 items-center justify-center rounded-xl bg-blue-600 text-sm font-bold text-white">
                DQ
              </div>
              <div>
                <CardTitle className="text-2xl">Data Quality Command Center</CardTitle>
                <CardDescription className="mt-1">
                  Sign in with your dashboard user account for {getApiBaseUrl()}.
                </CardDescription>
              </div>
            </CardHeader>
            <CardContent>
              <form className="space-y-4" onSubmit={handleSubmit}>
                <div className="space-y-2">
                  <Label htmlFor="username">Username</Label>
                  <Input
                    id="username"
                    value={username}
                    onChange={(event) => setUsername(event.target.value)}
                    placeholder="admin"
                    aria-label="Username"
                    autoComplete="username"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="password">Password</Label>
                  <Input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    placeholder="Password"
                    aria-label="Password"
                    autoComplete="current-password"
                  />
                </div>
                {error ? (
                  <Alert variant="destructive">
                    <KeyRound className="size-4" />
                    <AlertTitle>Access denied</AlertTitle>
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                ) : null}
                <Button className="w-full" disabled={loading || !username.trim() || !password} type="submit">
                  <UserRound className="size-4" />
                  {loading ? "Signing in..." : "Log in"}
                </Button>
              </form>
              <div className="mt-5 rounded-xl border bg-slate-50 p-4 text-sm text-slate-600 lg:hidden">
                <div className="mb-2 font-medium text-slate-900">Protected operations portal</div>
                Secure access, role-based dashboard, and API protected data.
              </div>
            </CardContent>
          </Card>
        </section>
      </div>
    </main>
  )
}

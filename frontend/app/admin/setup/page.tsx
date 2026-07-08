"use client"

import { useEffect, useMemo, useState } from "react"
import {
  AlertTriangle,
  CheckCircle2,
  CircleDashed,
  Database,
  FileCheck2,
  KeyRound,
  PlayCircle,
  RefreshCw,
  Send,
  Server,
  Table2,
} from "lucide-react"

import { AppShell } from "@/components/app-shell"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { EnterpriseMetricCard } from "@/components/ui-custom/metric-card"
import { PageHeader } from "@/components/ui-custom/page-header"
import { StatusBadge } from "@/components/ui-custom/status-badge"
import { api, getApiBaseUrl, getStoredApiToken } from "@/lib/api-client"
import { formatDateTime } from "@/lib/formatters"
import type { RunSummary } from "@/lib/types"

type CheckStatus = "PASS" | "FAIL" | "WARN" | "INFO" | "CHECKING"

type SetupCheck = {
  id: string
  title: string
  description: string
  status: CheckStatus
  detail: string
  action: string
  icon: typeof CheckCircle2
}

function statusIcon(status: CheckStatus) {
  if (status === "PASS") return <CheckCircle2 className="size-4 text-green-600" />
  if (status === "FAIL") return <AlertTriangle className="size-4 text-red-600" />
  if (status === "WARN") return <AlertTriangle className="size-4 text-amber-600" />
  return <CircleDashed className="size-4 text-blue-600" />
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Check failed unexpectedly."
}

export default function SetupPage() {
  const [checks, setChecks] = useState<SetupCheck[]>([])
  const [latestRun, setLatestRun] = useState<RunSummary | null>(null)
  const [lastChecked, setLastChecked] = useState("")
  const [runningChecks, setRunningChecks] = useState(false)
  const [message, setMessage] = useState("")

  async function runSetupChecks() {
    setMessage("")
    setChecks(baseChecks("CHECKING"))

    const token = getStoredApiToken()
    const nextChecks = baseChecks("INFO")

    nextChecks[0] = {
      ...nextChecks[0],
      status: getApiBaseUrl() && token ? "PASS" : "WARN",
      detail: getApiBaseUrl()
        ? `Frontend points to ${getApiBaseUrl()}${token ? " and has an API token in session/env." : " but no API token is available."}`
        : "NEXT_PUBLIC_API_BASE_URL is not configured.",
      action: token ? "No action required." : "Log in again or set NEXT_PUBLIC_API_TOKEN in frontend/.env.local.",
    }

    try {
      const health = await api.health()
      nextChecks[1] = {
        ...nextChecks[1],
        status: health.status === "ok" ? "PASS" : "WARN",
        detail: `FastAPI health endpoint returned ${health.status}.`,
        action: "Keep uvicorn running while using the frontend.",
      }
    } catch (err) {
      nextChecks[1] = {
        ...nextChecks[1],
        status: "FAIL",
        detail: errorMessage(err),
        action: "Start backend with uvicorn api.app:app --reload.",
      }
    }

    try {
      await api.runs()
      nextChecks[2] = {
        ...nextChecks[2],
        status: "PASS",
        detail: "Protected API request succeeded with the current X-API-Key token.",
        action: "No action required.",
      }
    } catch (err) {
      nextChecks[2] = {
        ...nextChecks[2],
        status: "FAIL",
        detail: errorMessage(err),
        action: "Use the exact API_TOKEN from backend .env on the login screen.",
      }
    }

    try {
      const ready = await api.ready()
      nextChecks[3] = {
        ...nextChecks[3],
        status: ready.status === "ready" ? "PASS" : "FAIL",
        detail: `Monitoring database is ${ready.database ?? ready.status}.`,
        action: ready.status === "ready" ? "No action required." : "Check DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, and DB_NAME.",
      }
    } catch (err) {
      nextChecks[3] = {
        ...nextChecks[3],
        status: "FAIL",
        detail: errorMessage(err),
        action: "Run python cli.py init-db after confirming PostgreSQL is running.",
      }
    }

    try {
      const runs = await api.runs()
      const latest = runs[0] ?? null
      setLatestRun(latest)
      nextChecks[4] = {
        ...nextChecks[4],
        status: runs.length ? "PASS" : "WARN",
        detail: runs.length
          ? `Monitoring tables are readable. Latest run is #${latest?.run_id}.`
          : "Monitoring tables are reachable but no runs exist yet.",
        action: runs.length ? "No action required." : "Run checks once to populate run history.",
      }
      nextChecks[5] = {
        ...nextChecks[5],
        status: runs.length ? "PASS" : "WARN",
        detail: runs.length
          ? `Previous data extraction completed at ${formatDateTime(latest?.run_time)}.`
          : "No completed run exists, so source extraction has not been verified from the UI.",
        action: "Use Run Checks Now to validate source DB access.",
      }
    } catch (err) {
      nextChecks[4] = {
        ...nextChecks[4],
        status: "FAIL",
        detail: errorMessage(err),
        action: "Initialize monitoring tables with python cli.py init-db.",
      }
      nextChecks[5] = {
        ...nextChecks[5],
        status: "WARN",
        detail: "Source DB cannot be inferred until monitoring tables are reachable.",
        action: "Fix monitoring DB first, then run checks.",
      }
    }

    try {
      const rules = await api.rules()
      nextChecks[6] = {
        ...nextChecks[6],
        status: rules.length ? "PASS" : "WARN",
        detail: rules.length ? `${rules.length} active rule rows loaded from rules.yaml.` : "Rules endpoint returned no flattened rules.",
        action: rules.length ? "No action required." : "Check config/rules.yaml and config/rules.example.yaml.",
      }
    } catch (err) {
      nextChecks[6] = {
        ...nextChecks[6],
        status: "FAIL",
        detail: errorMessage(err),
        action: "Validate config/rules.yaml syntax.",
      }
    }

    nextChecks[7] = {
      ...nextChecks[7],
      status: "INFO",
      detail: "Notification readiness is configured through backend .env variables and notification modules.",
      action: "Open Notification Center for channel-level setup placeholders.",
    }

    setChecks(nextChecks)
    setLastChecked(formatDateTime(new Date()))
  }

  async function runChecksNow() {
    setRunningChecks(true)
    setMessage("Running checks from backend. This can take a moment.")
    try {
      const response = await api.runChecks()
      setMessage(response.success ? "Checks completed successfully." : "Checks completed with errors. Review backend logs.")
      await runSetupChecks()
    } catch (err) {
      setMessage(errorMessage(err))
    } finally {
      setRunningChecks(false)
    }
  }

  useEffect(() => {
    runSetupChecks()
  }, [])

  const summary = useMemo(() => {
    return {
      pass: checks.filter((check) => check.status === "PASS").length,
      warn: checks.filter((check) => check.status === "WARN").length,
      fail: checks.filter((check) => check.status === "FAIL").length,
      total: checks.length,
    }
  }, [checks])

  return (
    <AppShell>
      <PageHeader
        eyebrow="Administration"
        title="Setup Wizard"
        subtitle="Live readiness checklist for local development, Docker, API auth, database access, rules, and monitoring tables."
        onRefresh={runSetupChecks}
        actions={
          <Button onClick={runChecksNow} disabled={runningChecks}>
            <PlayCircle className="size-4" />
            {runningChecks ? "Running..." : "Run Checks Now"}
          </Button>
        }
      />

      {message ? (
        <Card className="rounded-xl border-blue-100 bg-blue-50">
          <CardContent className="p-4 text-sm text-blue-700">{message}</CardContent>
        </Card>
      ) : null}

      <div className="grid gap-4 md:grid-cols-4">
        <EnterpriseMetricCard title="Checks Passing" value={summary.pass} description={`${summary.total} readiness checks`} icon={CheckCircle2} tone="green" />
        <EnterpriseMetricCard title="Warnings" value={summary.warn} description="Needs follow-up" icon={AlertTriangle} tone="amber" />
        <EnterpriseMetricCard title="Failures" value={summary.fail} description="Blocking setup" icon={AlertTriangle} tone="red" />
        <EnterpriseMetricCard title="Latest Run" value={latestRun?.run_id ?? "-"} description={lastChecked ? `Checked ${lastChecked}` : "Not checked yet"} icon={RefreshCw} tone="blue" />
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {(checks.length ? checks : baseChecks("CHECKING")).map((check) => {
          const Icon = check.icon
          return (
            <Card className="rounded-xl shadow-sm" key={check.id}>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  {statusIcon(check.status)}
                  {check.title}
                </CardTitle>
                <CardDescription>{check.description}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between gap-3">
                  <StatusBadge status={check.status} />
                  <Icon className="size-5 text-slate-400" />
                </div>
                <div className="rounded-xl border bg-slate-50 p-3 text-sm text-slate-600">
                  <div className="font-medium text-slate-900">Result</div>
                  <p className="mt-1">{check.detail}</p>
                </div>
                <div className="text-sm text-slate-500">
                  <span className="font-medium text-slate-700">Next action: </span>
                  {check.action}
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </AppShell>
  )
}

function baseChecks(status: CheckStatus): SetupCheck[] {
  return [
    {
      id: "frontend-env",
      title: "Frontend environment",
      description: "NEXT_PUBLIC_API_BASE_URL and API token availability.",
      status,
      detail: "Waiting for frontend environment check.",
      action: "Confirm frontend/.env.local and restart Next.js after changes.",
      icon: FileCheck2,
    },
    {
      id: "api-health",
      title: "FastAPI health",
      description: "Public backend health endpoint.",
      status,
      detail: "Waiting for API health check.",
      action: "Start uvicorn if this check fails.",
      icon: Server,
    },
    {
      id: "api-auth",
      title: "API auth status",
      description: "Protected X-API-Key request validation.",
      status,
      detail: "Waiting for API authentication check.",
      action: "Use the API_TOKEN from backend .env.",
      icon: KeyRound,
    },
    {
      id: "monitor-db",
      title: "Monitoring DB connection",
      description: "Backend readiness check against PostgreSQL.",
      status,
      detail: "Waiting for database readiness check.",
      action: "Check PostgreSQL and database environment variables.",
      icon: Database,
    },
    {
      id: "monitor-tables",
      title: "Monitoring tables",
      description: "Run history endpoint confirms table readability.",
      status,
      detail: "Waiting for monitoring table check.",
      action: "Run python cli.py init-db if tables are missing.",
      icon: Table2,
    },
    {
      id: "source-db",
      title: "Source DB connection",
      description: "Inferred from successful historical data quality runs.",
      status,
      detail: "Waiting for source DB inference.",
      action: "Run checks to verify source extraction.",
      icon: Database,
    },
    {
      id: "rules",
      title: "rules.yaml status",
      description: "Rules Catalog API validates flattened YAML rules.",
      status,
      detail: "Waiting for rules check.",
      action: "Fix YAML if this check fails.",
      icon: FileCheck2,
    },
    {
      id: "notifications",
      title: "Notification config",
      description: "Mailtrap, Slack, and Teams setup readiness.",
      status,
      detail: "Waiting for notification config check.",
      action: "Review backend .env notification variables.",
      icon: Send,
    },
  ]
}


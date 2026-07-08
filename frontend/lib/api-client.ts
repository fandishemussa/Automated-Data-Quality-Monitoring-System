"use client"

import type {
  AlertRecord,
  AppUser,
  AuditLog,
  CheckRunResponse,
  CheckResult,
  CleanableIssue,
  CleaningJob,
  CleaningPayload,
  CleaningPreview,
  CleaningSuggestion,
  CreateUserPayload,
  IssueDetail,
  LineageEdge,
  LoginResponse,
  ProfileResult,
  ProfileUpdatePayload,
  ProfileUpdateRequest,
  RuleCatalogRow,
  RunSummary,
  SlaResult,
  UpdateUserPayload,
} from "@/lib/types"
import { API_TOKEN_STORAGE_KEY, USER_NAME_STORAGE_KEY, USER_ROLE_STORAGE_KEY } from "@/lib/constants"

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "http://localhost:8000"

export function getApiBaseUrl(): string {
  return API_BASE_URL
}

export function getStoredApiToken(): string {
  if (typeof window === "undefined") {
    return process.env.NEXT_PUBLIC_API_TOKEN ?? ""
  }

  return localStorage.getItem(API_TOKEN_STORAGE_KEY) ?? process.env.NEXT_PUBLIC_API_TOKEN ?? ""
}

export function setStoredApiToken(token: string) {
  if (typeof window !== "undefined") {
    localStorage.setItem(API_TOKEN_STORAGE_KEY, token)
  }
}

export function clearStoredApiToken() {
  if (typeof window !== "undefined") {
    localStorage.removeItem(API_TOKEN_STORAGE_KEY)
    localStorage.removeItem(USER_NAME_STORAGE_KEY)
    localStorage.removeItem(USER_ROLE_STORAGE_KEY)
  }
}

export function setStoredUserSession(token: string, user: AppUser) {
  if (typeof window !== "undefined") {
    localStorage.setItem(API_TOKEN_STORAGE_KEY, token)
    localStorage.setItem(USER_NAME_STORAGE_KEY, user.username)
    localStorage.setItem(USER_ROLE_STORAGE_KEY, String(user.role ?? "viewer"))
  }
}

export function getStoredUserRole(): string {
  if (typeof window === "undefined") {
    return process.env.NEXT_PUBLIC_USER_ROLE ?? "admin"
  }

  return localStorage.getItem(USER_ROLE_STORAGE_KEY) ?? process.env.NEXT_PUBLIC_USER_ROLE ?? "admin"
}

export function getStoredUserName(): string {
  if (typeof window === "undefined") {
    return process.env.NEXT_PUBLIC_USER_NAME ?? "api_user"
  }

  return localStorage.getItem(USER_NAME_STORAGE_KEY) ?? process.env.NEXT_PUBLIC_USER_NAME ?? "api_user"
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getStoredApiToken()
  const isPublicEndpoint = path === "/api/v1/health" || path === "/api/v1/auth/login" || path === "/ready"

  if (!token && !isPublicEndpoint) {
    throw new Error(
      "Missing dashboard session. Open /login and sign in with your username and password."
    )
  }

  let response: Response

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { "X-API-Key": token } : {}),
        "X-User": getStoredUserName(),
        "X-User-Role": getStoredUserRole(),
        ...(init?.headers ?? {}),
      },
    })
  } catch {
    throw new Error(
      `Cannot reach FastAPI at ${API_BASE_URL}. Start the backend with "uvicorn api.app:app --reload" and confirm FRONTEND_URL allows http://localhost:3000.`
    )
  }

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`
    try {
      const body = await response.json()
      detail = body.detail ?? detail
    } catch {
      // Keep the generic message when the response is not JSON.
    }
    throw new Error(detail)
  }

  return response.json() as Promise<T>
}

export const api = {
  health: () => requestJson<{ status: string }>("/api/v1/health"),
  login: (payload: { username: string; password: string }) =>
    requestJson<LoginResponse>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  ready: () => requestJson<{ status: string; database?: string }>("/ready"),
  runs: () => requestJson<RunSummary[]>("/api/v1/runs?limit=25"),
  latestRun: () => requestJson<RunSummary>("/api/v1/runs/latest"),
  results: (runId?: number) =>
    requestJson<CheckResult[]>(runId ? `/api/v1/results/${runId}` : "/api/v1/results?limit=500"),
  issues: (runId: number) => requestJson<IssueDetail[]>(`/api/v1/issues/${runId}`),
  alerts: (isResolved?: boolean) => {
    const query = typeof isResolved === "boolean" ? `?is_resolved=${isResolved}` : ""
    return requestJson<AlertRecord[]>(`/api/v1/alerts${query}`)
  },
  resolveAlert: (alertId: number) =>
    requestJson<AlertRecord>(
      `/api/v1/alerts/${alertId}/resolve`,
      { method: "PATCH" }
    ),
  acknowledgeAlert: (alertId: number) =>
    requestJson<AlertRecord>(`/api/v1/alerts/${alertId}/acknowledge`, { method: "PATCH" }),
  assignAlert: (alertId: number, assignedTo: string) =>
    requestJson<AlertRecord>(`/api/v1/alerts/${alertId}/assign`, {
      method: "PATCH",
      body: JSON.stringify({ assigned_to: assignedTo }),
    }),
  escalateAlert: (alertId: number) =>
    requestJson<AlertRecord>(`/api/v1/alerts/${alertId}/escalate`, { method: "PATCH" }),
  sla: () => requestJson<SlaResult[]>("/api/v1/sla?limit=500"),
  lineage: () => requestJson<LineageEdge[]>("/api/v1/lineage?limit=500"),
  profiling: () => requestJson<ProfileResult[]>("/api/v1/profiling?limit=500"),
  rules: () => requestJson<RuleCatalogRow[]>("/api/v1/rules"),
  auditLogs: () => requestJson<AuditLog[]>("/api/v1/audit-logs?limit=500"),
  runChecks: () => requestJson<CheckRunResponse>("/api/v1/checks/run", { method: "POST" }),
  cleanableIssues: () => requestJson<CleanableIssue[]>("/api/v1/issues/cleanable"),
  cleaningSuggestions: (issueId: number) =>
    requestJson<{ issue_id: number; suggestions: CleaningSuggestion[] }>(`/api/v1/issues/${issueId}/suggestions`),
  previewCleaning: (payload: CleaningPayload) =>
    requestJson<CleaningPreview>("/api/v1/cleaning/preview", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  createCleaningJob: (payload: CleaningPayload) =>
    requestJson<CleaningJob>("/api/v1/cleaning/jobs", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  cleaningJobs: () => requestJson<CleaningJob[]>("/api/v1/cleaning/jobs"),
  cleaningJob: (jobId: number) => requestJson<CleaningJob>(`/api/v1/cleaning/jobs/${jobId}`),
  approveCleaningJob: (jobId: number) =>
    requestJson<CleaningJob>(`/api/v1/cleaning/jobs/${jobId}/approve`, { method: "PATCH" }),
  executeCleaningJob: (jobId: number) =>
    requestJson<CleaningJob>(`/api/v1/cleaning/jobs/${jobId}/execute`, { method: "POST" }),
  rollbackCleaningJob: (jobId: number) =>
    requestJson<CleaningJob>(`/api/v1/cleaning/jobs/${jobId}/rollback`, { method: "POST" }),
  verifyCleaningJob: (jobId: number) =>
    requestJson<Record<string, unknown>>(`/api/v1/cleaning/jobs/${jobId}/verify`, { method: "POST" }),
  updateIssueStatus: (issueId: number, payload: Record<string, unknown>) =>
    requestJson<Record<string, unknown>>(`/api/v1/issues/${issueId}/status`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  users: () => requestJson<AppUser[]>("/api/v1/users"),
  me: () => requestJson<AppUser>("/api/v1/users/me"),
  submitProfileUpdate: (payload: ProfileUpdatePayload) =>
    requestJson<ProfileUpdateRequest>("/api/v1/users/me/profile-updates", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  profileUpdateRequests: () => requestJson<ProfileUpdateRequest[]>("/api/v1/users/profile-updates"),
  approveProfileUpdate: (updateId: number, reviewNotes = "") =>
    requestJson<ProfileUpdateRequest>(`/api/v1/users/profile-updates/${updateId}/approve`, {
      method: "PATCH",
      body: JSON.stringify({ review_notes: reviewNotes }),
    }),
  rejectProfileUpdate: (updateId: number, reviewNotes = "") =>
    requestJson<ProfileUpdateRequest>(`/api/v1/users/profile-updates/${updateId}/reject`, {
      method: "PATCH",
      body: JSON.stringify({ review_notes: reviewNotes }),
    }),
  createUser: (payload: CreateUserPayload) =>
    requestJson<AppUser>("/api/v1/users", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateUser: (userId: number, payload: UpdateUserPayload) =>
    requestJson<AppUser>(`/api/v1/users/${userId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  deactivateUser: (userId: number) =>
    requestJson<AppUser>(`/api/v1/users/${userId}`, {
      method: "DELETE",
    }),
}

export const getLatestRun = api.latestRun
export const getRuns = api.runs
export const getResults = api.results
export const getAlerts = api.alerts
export const resolveAlert = api.resolveAlert
export const getSla = api.sla
export const getLineage = api.lineage
export const getProfiling = api.profiling
export const getRules = api.rules
export const getAuditLogs = api.auditLogs
export const runChecks = api.runChecks

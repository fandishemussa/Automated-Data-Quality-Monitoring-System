export const enterpriseTheme = {
  colors: {
    primary: "#2563eb",
    success: "#16a34a",
    warning: "#d97706",
    danger: "#dc2626",
    muted: "#64748b",
    slate: "#0f172a",
  },
  chartColors: ["#2563eb", "#16a34a", "#d97706", "#dc2626", "#7c3aed", "#0891b2"],
}

export type StatusTone = "success" | "warning" | "danger" | "neutral" | "info"

export function getStatusTone(status?: string): StatusTone {
  const normalized = String(status ?? "").toUpperCase()
  if (["PASS", "PASSED", "RESOLVED", "HEALTHY", "OK"].includes(normalized)) return "success"
  if (["WARN", "WARNING", "SKIPPED", "INFO", "ACKNOWLEDGED", "INVESTIGATING"].includes(normalized)) return "warning"
  if (["FAIL", "FAILED", "CRITICAL", "HIGH", "OPEN", "ESCALATED", "BREACHED"].includes(normalized)) return "danger"
  return "neutral"
}

export function getSeverityTone(severity?: string): StatusTone {
  const normalized = String(severity ?? "").toUpperCase()
  if (["CRITICAL", "HIGH"].includes(normalized)) return "danger"
  if (["MEDIUM", "WARNING"].includes(normalized)) return "warning"
  if (["LOW", "INFO"].includes(normalized)) return "info"
  return "neutral"
}


"use client"

import { GitBranch, ShieldAlert, Wrench } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { IssueStatusBadge } from "@/components/remediation/issue-status-badge"
import { SeverityBadge } from "@/components/ui-custom/severity-badge"
import type { CleanableIssue, CleaningSuggestion } from "@/lib/types"

type IssueDetailDrawerProps = {
  issue?: CleanableIssue
  open: boolean
  suggestions: CleaningSuggestion[]
  onOpenChange: (open: boolean) => void
  onCreateJob: (issue: CleanableIssue) => void
  onStatusChange: (issue: CleanableIssue, status: string) => void
}

export function IssueDetailDrawer({
  issue,
  open,
  suggestions,
  onOpenChange,
  onCreateJob,
  onStatusChange,
}: IssueDetailDrawerProps) {
  if (!issue) return null

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full overflow-y-auto sm:max-w-2xl">
        <SheetHeader>
          <SheetTitle>Issue #{issue.id}</SheetTitle>
          <SheetDescription>
            {issue.dataset_name}.{issue.column_name} remediation context
          </SheetDescription>
        </SheetHeader>
        <div className="space-y-4 px-4 pb-4">
          <div className="flex flex-wrap gap-2">
            <IssueStatusBadge status={issue.issue_status} />
            <SeverityBadge severity={issue.severity} />
          </div>
          <Card className="rounded-xl">
            <CardHeader>
              <CardTitle>Issue Details</CardTitle>
              <CardDescription>{issue.check_type}</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3 text-sm">
              <Info label="Dataset" value={issue.dataset_name} />
              <Info label="Column" value={issue.column_name} />
              <Info label="Row identifier" value={issue.row_identifier} />
              <Info label="Bad value" value={issue.bad_value} />
              <Info label="Reason" value={issue.reason} />
            </CardContent>
          </Card>
          <Tabs defaultValue="suggestions">
            <TabsList>
              <TabsTrigger value="suggestions">Suggested Actions</TabsTrigger>
              <TabsTrigger value="context">Related Context</TabsTrigger>
              <TabsTrigger value="sample">Sample Row</TabsTrigger>
            </TabsList>
            <TabsContent value="suggestions" className="mt-4 space-y-3">
              {suggestions.map((suggestion) => (
                <div className="rounded-xl border p-3" key={suggestion.action}>
                  <div className="font-medium">{suggestion.action}</div>
                  <p className="text-sm text-slate-500">{suggestion.description}</p>
                </div>
              ))}
            </TabsContent>
            <TabsContent value="context" className="mt-4 space-y-3">
              <ContextCard icon={ShieldAlert} title="Related alert" value="Shown when linked alert data is available." />
              <ContextCard icon={GitBranch} title="Lineage impact" value="Use Data Lineage to inspect upstream/downstream dependencies." />
            </TabsContent>
            <TabsContent value="sample" className="mt-4">
              <pre className="max-h-80 overflow-auto rounded-xl bg-slate-950 p-3 text-xs text-slate-100">
                {issue.sample_row || "No sample row stored."}
              </pre>
            </TabsContent>
          </Tabs>
          <Separator />
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => onCreateJob(issue)}>
              <Wrench className="size-4" />
              Create Cleaning Job
            </Button>
            <Button variant="outline" onClick={() => onStatusChange(issue, "ASSIGNED")}>Assign</Button>
            <Button variant="outline" onClick={() => onStatusChange(issue, "FALSE_POSITIVE")}>False Positive</Button>
            <Button variant="outline" onClick={() => onStatusChange(issue, "IGNORED")}>Ignore</Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}

function Info({ label, value }: { label: string; value?: string | number | null }) {
  return (
    <div className="grid grid-cols-[140px_1fr] gap-3">
      <div className="text-slate-500">{label}</div>
      <div className="font-medium text-slate-900">{value ?? "-"}</div>
    </div>
  )
}

function ContextCard({
  icon: Icon,
  title,
  value,
}: {
  icon: typeof ShieldAlert
  title: string
  value: string
}) {
  return (
    <div className="flex gap-3 rounded-xl border p-3">
      <Icon className="mt-0.5 size-4 text-blue-600" />
      <div>
        <div className="font-medium">{title}</div>
        <p className="text-sm text-slate-500">{value}</p>
      </div>
    </div>
  )
}


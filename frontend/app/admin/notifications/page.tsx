"use client"

import { Mail, MessageSquare, Send } from "lucide-react"

import { AppShell } from "@/components/app-shell"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { PageHeader } from "@/components/ui-custom/page-header"
import { StatusBadge } from "@/components/ui-custom/status-badge"

const channels = [
  { name: "Mailtrap Email", icon: Mail, status: "Configured in backend .env" },
  { name: "Slack Webhook", icon: MessageSquare, status: "Configured in backend .env" },
  { name: "Microsoft Teams", icon: Send, status: "Configured in backend .env" },
]

export default function NotificationsPage() {
  return (
    <AppShell>
      <PageHeader eyebrow="Administration" title="Notification Center" subtitle="Notification channels, delivery readiness, and test action placeholders." />
      <div className="grid gap-4 md:grid-cols-3">
        {channels.map((channel) => {
          const Icon = channel.icon
          return (
            <Card className="rounded-xl shadow-sm" key={channel.name}>
              <CardHeader>
                <CardTitle className="flex items-center gap-2"><Icon className="size-4" /> {channel.name}</CardTitle>
                <CardDescription>{channel.status}</CardDescription>
              </CardHeader>
              <CardContent className="flex items-center justify-between">
                <StatusBadge status="INFO" />
                <Button variant="outline" disabled>Test</Button>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </AppShell>
  )
}


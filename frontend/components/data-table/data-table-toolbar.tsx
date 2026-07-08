"use client"

import { Download, Search } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

type DataTableToolbarProps = {
  searchValue: string
  onSearchChange: (value: string) => void
  placeholder?: string
  onExport?: () => void
}

export function DataTableToolbar({
  searchValue,
  onSearchChange,
  placeholder = "Search table...",
  onExport,
}: DataTableToolbarProps) {
  return (
    <div className="flex flex-col gap-3 border-b p-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="relative w-full max-w-md">
        <Search className="absolute left-2.5 top-2.5 size-4 text-slate-400" />
        <Input
          value={searchValue}
          onChange={(event) => onSearchChange(event.target.value)}
          className="pl-8"
          placeholder={placeholder}
        />
      </div>
      {onExport ? (
        <Button variant="outline" onClick={onExport}>
          <Download className="size-4" />
          Export CSV
        </Button>
      ) : null}
    </div>
  )
}


"use client"

import { useMemo, useState } from "react"
import {
  ColumnDef,
  ColumnFiltersState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  SortingState,
  useReactTable,
  VisibilityState,
} from "@tanstack/react-table"

import { DataTablePagination } from "@/components/data-table/data-table-pagination"
import { DataTableToolbar } from "@/components/data-table/data-table-toolbar"
import { EmptyState } from "@/components/ui-custom/empty-state"
import { LoadingState } from "@/components/ui-custom/loading-state"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

type EnterpriseDataTableProps<TData, TValue> = {
  columns: ColumnDef<TData, TValue>[]
  data: TData[]
  loading?: boolean
  emptyTitle?: string
  emptyDescription?: string
  searchPlaceholder?: string
  enableExport?: boolean
}

function exportCsv<TData>(rows: TData[]) {
  const csv = rows
    .map((row) =>
      Object.values(row as Record<string, unknown>)
        .map((value) => `"${String(value ?? "").replaceAll('"', '""')}"`)
        .join(",")
    )
    .join("\n")
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" })
  const url = URL.createObjectURL(blob)
  const link = document.createElement("a")
  link.href = url
  link.download = `data-quality-export-${new Date().toISOString().slice(0, 19)}.csv`
  link.click()
  URL.revokeObjectURL(url)
}

export function EnterpriseDataTable<TData, TValue>({
  columns,
  data,
  loading = false,
  emptyTitle = "No records found",
  emptyDescription = "There is no data available for this view.",
  searchPlaceholder,
  enableExport = true,
}: EnterpriseDataTableProps<TData, TValue>) {
  const [sorting, setSorting] = useState<SortingState>([])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [globalFilter, setGlobalFilter] = useState("")
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({})

  const table = useReactTable({
    data,
    columns,
    state: { sorting, columnFilters, globalFilter, columnVisibility },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onGlobalFilterChange: setGlobalFilter,
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize: 10 } },
  })

  const visibleRows = useMemo(() => table.getFilteredRowModel().rows.map((row) => row.original), [table])

  return (
    <div className="overflow-hidden rounded-xl border bg-white shadow-sm">
      <DataTableToolbar
        searchValue={globalFilter ?? ""}
        onSearchChange={setGlobalFilter}
        placeholder={searchPlaceholder}
        onExport={enableExport ? () => exportCsv(visibleRows) : undefined}
      />
      {loading ? (
        <div className="p-4">
          <LoadingState rows={5} />
        </div>
      ) : table.getRowModel().rows.length ? (
        <>
          <Table>
            <TableHeader>
              {table.getHeaderGroups().map((headerGroup) => (
                <TableRow key={headerGroup.id} className="bg-slate-50">
                  {headerGroup.headers.map((header) => (
                    <TableHead key={header.id} className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      {header.isPlaceholder
                        ? null
                        : flexRender(header.column.columnDef.header, header.getContext())}
                    </TableHead>
                  ))}
                </TableRow>
              ))}
            </TableHeader>
            <TableBody>
              {table.getRowModel().rows.map((row) => (
                <TableRow key={row.id}>
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id} className="max-w-md text-slate-700">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <DataTablePagination table={table} />
        </>
      ) : (
        <div className="p-4">
          <EmptyState title={emptyTitle} description={emptyDescription} />
        </div>
      )}
    </div>
  )
}


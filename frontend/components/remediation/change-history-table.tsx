import { EnterpriseDataTable } from "@/components/data-table/data-table"
import { formatDateTime } from "@/lib/formatters"
import type { CleaningChangeLog } from "@/lib/types"

const columns = [
  { accessorKey: "created_at", header: "Created", cell: ({ row }: { row: { original: CleaningChangeLog } }) => formatDateTime(row.original.created_at) },
  { accessorKey: "dataset_name", header: "Dataset" },
  { accessorKey: "table_name", header: "Table" },
  { accessorKey: "column_name", header: "Column" },
  { accessorKey: "row_identifier", header: "Row Identifier" },
  { accessorKey: "old_value", header: "Old Value" },
  { accessorKey: "new_value", header: "New Value" },
  { accessorKey: "change_reason", header: "Reason" },
]

export function ChangeHistoryTable({ rows }: { rows: CleaningChangeLog[] }) {
  return <EnterpriseDataTable columns={columns} data={rows} />
}


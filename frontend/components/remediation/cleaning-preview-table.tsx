import { EnterpriseDataTable } from "@/components/data-table/data-table"
import type { CleaningPreviewRow } from "@/lib/types"

const columns = [
  { accessorKey: "row_identifier", header: "Row Identifier" },
  { accessorKey: "old_value", header: "Old Value" },
  { accessorKey: "new_value", header: "New Value" },
  { accessorKey: "will_update", header: "Will Update", cell: ({ row }: { row: { original: CleaningPreviewRow } }) => String(row.original.will_update ?? false) },
]

export function CleaningPreviewTable({ rows }: { rows: CleaningPreviewRow[] }) {
  return <EnterpriseDataTable columns={columns} data={rows} enableExport={false} />
}


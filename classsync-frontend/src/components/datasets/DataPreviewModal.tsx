import { useEffect, useMemo, useRef } from "react"
import { useInfiniteQuery } from "@tanstack/react-query"
import {
  useReactTable,
  getCoreRowModel,
  ColumnDef,
  flexRender,
} from "@tanstack/react-table"
import { useVirtualizer } from "@tanstack/react-virtual"
import { Loader2, AlertCircle } from "lucide-react"

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog"
import { datasetsApi } from "@/lib/api"
import { cn } from "@/lib/utils"

type DataPreviewModalProps = {
  datasetId: number | null
  fileName?: string
  open: boolean
  onOpenChange: (open: boolean) => void
}

const PAGE_SIZE = 200

export function DataPreviewModal({
  datasetId,
  fileName,
  open,
  onOpenChange,
}: DataPreviewModalProps) {
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    isError,
    error,
  } = useInfiniteQuery({
    queryKey: ["dataset-preview", datasetId],
    queryFn: async ({ pageParam = 0 }) => {
      if (!datasetId) return null
      const res = await datasetsApi.preview(datasetId, {
        offset: pageParam,
        limit: PAGE_SIZE,
      })
      return res.data
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage) => {
      if (!lastPage) return undefined
      const nextOffset = lastPage.offset + lastPage.limit
      if (nextOffset >= lastPage.total_rows) return undefined
      return nextOffset
    },
    enabled: !!datasetId && open,
  })

  // Flatten rows
  const rows = useMemo(() => {
    return data?.pages.flatMap((page) => page?.rows || []) || []
  }, [data])

  const totalRows = data?.pages[0]?.total_rows || 0
  const columnsList: string[] = data?.pages[0]?.columns || []

  // Create columns definition
  const columns = useMemo<ColumnDef<Record<string, any>>[]>(
    () =>
      columnsList.map((col) => ({
        id: col,
        accessorFn: (row) => row[col],
        header: col,
        cell: (info: any) => info.getValue(),
      })),
    [columnsList]
  )

  const table = useReactTable({
    data: rows,
    columns,
    getCoreRowModel: getCoreRowModel(),
  })

  // Virtualization
  const parentRef = useRef<HTMLDivElement>(null)

  const rowVirtualizer = useVirtualizer({
    count: hasNextPage ? rows.length + 1 : rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 35, // Estimate row height
    overscan: 20,
  })

  useEffect(() => {
    const [lastItem] = [...rowVirtualizer.getVirtualItems()].reverse()
    if (!lastItem) return

    if (
      lastItem.index >= rows.length - 1 &&
      hasNextPage &&
      !isFetchingNextPage
    ) {
      fetchNextPage()
    }
  }, [
    hasNextPage,
    fetchNextPage,
    rows.length,
    isFetchingNextPage,
    rowVirtualizer.getVirtualItems(),
  ])

  const { getVirtualItems, getTotalSize } = rowVirtualizer
  const virtualRows = getVirtualItems()

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[90vw] h-[85vh] flex flex-col p-0 gap-0 overflow-hidden sm:rounded-xl">
        <DialogHeader className="p-6 pb-2 border-b shrink-0">
          <DialogTitle>Preview: {fileName}</DialogTitle>
          <DialogDescription>
            {isLoading ? (
              "Loading data..."
            ) : (
               <>
                Showing {rows.length} of {totalRows} rows loaded
               </>
            )}
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-hidden relative bg-card">
          {isLoading ? (
            <div className="flex items-center justify-center h-full">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : isError ? (
             <div className="flex flex-col items-center justify-center h-full text-destructive gap-2">
                <AlertCircle className="h-8 w-8" />
                <p>Failed to load data</p>
                <p className="text-sm text-muted-foreground">{(error as any)?.message}</p>
             </div>
          ) : (
            <div
              ref={parentRef}
              className="h-full w-full overflow-auto"
            >
              <div
                 style={{
                   height: `${getTotalSize()}px`,
                   width: '100%',
                   position: 'relative',
                 }}
              >
                <table className="w-full text-sm text-left border-collapse">
                    <thead className="sticky top-0 z-10 bg-muted/90 backdrop-blur supports-[backdrop-filter]:bg-muted/60 shadow-sm">
                      {table.getHeaderGroups().map((headerGroup) => (
                        <tr key={headerGroup.id}>
                          {headerGroup.headers.map((header) => (
                            <th
                              key={header.id}
                              className="h-10 px-3 py-2 text-xs font-bold uppercase tracking-wider text-muted-foreground border-b border-r border-border/50 last:border-r-0 truncate min-w-[150px]"
                            >
                              {flexRender(
                                header.column.columnDef.header,
                                header.getContext()
                              )}
                            </th>
                          ))}
                        </tr>
                      ))}
                    </thead>
                    <tbody>
                        {virtualRows.map((virtualRow) => {
                            const isLoaderRow = virtualRow.index > rows.length - 1
                            const row = rows[virtualRow.index]

                            return (
                                <tr
                                    key={virtualRow.index}
                                    style={{
                                        position: 'absolute',
                                        top: 0,
                                        left: 0,
                                        width: '100%',
                                        height: `${virtualRow.size}px`,
                                        transform: `translateY(${virtualRow.start}px)`
                                    }}
                                    className={cn(
                                        "hover:bg-muted/40 transition-colors border-b border-border/40",
                                        virtualRow.index % 2 !== 0 ? "bg-muted/20" : ""
                                    )}
                                >
                                    {isLoaderRow ? (
                                        <td colSpan={columns.length} className="px-3 py-2 text-center text-muted-foreground">
                                            Loading more...
                                        </td>
                                    ) : (
                                        table.getVisibleLeafColumns().map(column => {
                                            const value = row[column.id]
                                            return (
                                                <td key={column.id} className="px-3 py-2 border-r border-border/40 last:border-r-0 truncate max-w-[300px]" title={String(value)}>
                                                    {value !== null && value !== undefined ? String(value) : <span className="text-muted-foreground/30 italic">null</span>}
                                                </td>
                                            )
                                        })
                                    )}
                                </tr>
                            )
                        })}
                    </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}

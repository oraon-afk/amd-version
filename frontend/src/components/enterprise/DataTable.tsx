"use client";

import { motion } from "framer-motion";
import { ChevronLeft, ChevronRight, ChevronsUpDown, Columns3, Download, Search, SlidersHorizontal } from "lucide-react";
import { type ReactNode, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

type SortValue = string | number | null | undefined;

export type DataTableColumn<T> = {
  id: string;
  header: string;
  cell: (row: T) => ReactNode;
  sortValue?: (row: T) => SortValue;
  searchValue?: (row: T) => string;
  exportValue?: (row: T) => string | number | null | undefined;
  className?: string;
  enableHiding?: boolean;
};

export type DataTableFilter<T> = {
  id: string;
  label: string;
  predicate: (row: T) => boolean;
};

export function DataTable<T>({
  data,
  columns,
  getRowId,
  filters = [],
  searchPlaceholder = "Search table",
  emptyState,
  pageSize = 8,
  exportFilename = "table-export.csv",
}: {
  data: T[];
  columns: DataTableColumn<T>[];
  getRowId: (row: T) => string;
  filters?: DataTableFilter<T>[];
  searchPlaceholder?: string;
  emptyState?: ReactNode;
  pageSize?: number;
  exportFilename?: string;
}) {
  const [query, setQuery] = useState("");
  const [filterId, setFilterId] = useState("all");
  const [sort, setSort] = useState<{ id: string; direction: "asc" | "desc" } | null>(null);
  const [page, setPage] = useState(1);
  const [visibleColumns, setVisibleColumns] = useState(() => new Set(columns.map((column) => column.id)));

  const visibleColumnList = columns.filter((column) => visibleColumns.has(column.id));
  const activeFilter = filters.find((filter) => filter.id === filterId);

  const filteredRows = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    const rows = activeFilter ? data.filter(activeFilter.predicate) : data;
    const searched = normalizedQuery
      ? rows.filter((row) =>
          columns.some((column) =>
            valueForSearch(row, column).toLowerCase().includes(normalizedQuery),
          ),
        )
      : rows;

    if (!sort) return searched;
    const sortColumn = columns.find((column) => column.id === sort.id);
    if (!sortColumn) return searched;
    return [...searched].sort((a, b) => {
      const first = valueForSort(a, sortColumn);
      const second = valueForSort(b, sortColumn);
      const comparison = compareValues(first, second);
      return sort.direction === "asc" ? comparison : comparison * -1;
    });
  }, [activeFilter, columns, data, query, sort]);

  const pageCount = Math.max(1, Math.ceil(filteredRows.length / pageSize));
  const currentPage = Math.min(page, pageCount);
  const pageRows = filteredRows.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  function toggleSort(column: DataTableColumn<T>) {
    setPage(1);
    setSort((current) => {
      if (current?.id !== column.id) return { id: column.id, direction: "asc" };
      if (current.direction === "asc") return { id: column.id, direction: "desc" };
      return null;
    });
  }

  function toggleColumn(columnId: string) {
    setVisibleColumns((current) => {
      const next = new Set(current);
      if (next.has(columnId) && next.size > 1) next.delete(columnId);
      else next.add(columnId);
      return next;
    });
  }

  function exportCsv() {
    const header = visibleColumnList.map((column) => escapeCsv(column.header)).join(",");
    const rows = filteredRows.map((row) =>
      visibleColumnList
        .map((column) => escapeCsv(String(column.exportValue?.(row) ?? column.searchValue?.(row) ?? valueForSort(row, column) ?? "")))
        .join(","),
    );
    const blob = new Blob([[header, ...rows].join("\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = window.document.createElement("a");
    anchor.href = url;
    anchor.download = exportFilename;
    window.document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="min-w-0 space-y-4">
      <div className="flex min-w-0 flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
        <div className="flex min-w-0 flex-1 flex-col gap-3 sm:flex-row">
          <div className="relative min-w-0 flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            <Input
              value={query}
              onChange={(event) => {
                setQuery(event.target.value);
                setPage(1);
              }}
              placeholder={searchPlaceholder}
              className="pl-10"
              aria-label={searchPlaceholder}
            />
          </div>
          {filters.length > 0 && (
            <label className="relative min-w-52">
              <span className="sr-only">Filter table</span>
              <SlidersHorizontal className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
              <select
                value={filterId}
                onChange={(event) => {
                  setFilterId(event.target.value);
                  setPage(1);
                }}
                className="h-11 w-full rounded-lg border border-line bg-elevated px-10 text-sm outline-none transition focus:border-info/70"
              >
                <option value="all">All records</option>
                {filters.map((filter) => (
                  <option key={filter.id} value={filter.id}>
                    {filter.label}
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <details className="relative">
            <summary className="inline-flex h-10 cursor-pointer list-none items-center gap-2 rounded-lg border border-line bg-elevated px-3 text-sm font-semibold text-foreground transition hover:border-info/40">
              <Columns3 className="h-4 w-4" />
              Columns
            </summary>
            <div className="absolute right-0 z-20 mt-2 w-56 rounded-lg border border-line bg-panel p-2 shadow-panel">
              {columns.map((column) => (
                <label key={column.id} className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-2 text-sm text-muted hover:bg-elevated hover:text-foreground">
                  <input
                    type="checkbox"
                    checked={visibleColumns.has(column.id)}
                    disabled={column.enableHiding === false}
                    onChange={() => toggleColumn(column.id)}
                    className="h-4 w-4 accent-primary"
                  />
                  {column.header}
                </label>
              ))}
            </div>
          </details>
          <Button type="button" variant="secondary" onClick={exportCsv}>
            <Download className="h-4 w-4" />
            CSV
          </Button>
        </div>
      </div>

      <div className="max-w-full overflow-x-auto rounded-lg border border-line bg-card/60">
        <table className="w-full min-w-[820px] table-fixed border-collapse text-sm">
          <thead className="bg-elevated">
            <tr className="border-b border-line text-left text-xs uppercase tracking-[0.14em] text-muted">
              {visibleColumnList.map((column) => (
                <th key={column.id} className={cn("px-3 py-3 font-semibold", column.className)}>
                  <button
                    type="button"
                    onClick={() => toggleSort(column)}
                    className="inline-flex items-center gap-1 text-left transition hover:text-foreground"
                  >
                    {column.header}
                    <ChevronsUpDown className="h-3.5 w-3.5" />
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pageRows.map((row, rowIndex) => (
              <motion.tr
                key={getRowId(row)}
                initial={{ y: 25, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: rowIndex * 0.04, duration: 0.35, ease: "easeOut" }}
                className="border-b border-line/70 transition-all duration-200 hover:-translate-y-[2px] hover:bg-elevated/70 hover:shadow-[0_20px_25px_-5px_rgba(124,77,255,0.15)]"
              >
                {visibleColumnList.map((column) => (
                  <td key={column.id} className={cn("min-w-0 break-words px-3 py-4 align-top", column.className)}>
                    <div className="min-w-0 overflow-hidden">{column.cell(row)}</div>
                  </td>
                ))}
              </motion.tr>
            ))}
          </tbody>
        </table>
        {filteredRows.length === 0 && (
          <div className="p-5">
            {emptyState ?? <p className="rounded-lg border border-line bg-elevated p-4 text-sm text-muted">No matching records found.</p>}
          </div>
        )}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-muted">
        <span>
          Showing {filteredRows.length === 0 ? 0 : (currentPage - 1) * pageSize + 1}-
          {Math.min(currentPage * pageSize, filteredRows.length)} of {filteredRows.length}
        </span>
        <div className="flex items-center gap-2">
          <Button type="button" variant="secondary" size="sm" disabled={currentPage === 1} onClick={() => setPage((value) => Math.max(1, value - 1))}>
            <ChevronLeft className="h-4 w-4" />
            Prev
          </Button>
          <span className="min-w-20 text-center">
            Page {currentPage} of {pageCount}
          </span>
          <Button type="button" variant="secondary" size="sm" disabled={currentPage === pageCount} onClick={() => setPage((value) => Math.min(pageCount, value + 1))}>
            Next
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}

function valueForSearch<T>(row: T, column: DataTableColumn<T>) {
  return String(column.searchValue?.(row) ?? column.exportValue?.(row) ?? column.sortValue?.(row) ?? "");
}

function valueForSort<T>(row: T, column: DataTableColumn<T>) {
  return column.sortValue?.(row) ?? column.exportValue?.(row) ?? column.searchValue?.(row) ?? "";
}

function compareValues(first: SortValue, second: SortValue) {
  if (typeof first === "number" && typeof second === "number") return first - second;
  return String(first ?? "").localeCompare(String(second ?? ""), undefined, { numeric: true, sensitivity: "base" });
}

function escapeCsv(value: string) {
  const escaped = value.replaceAll('"', '""');
  return /[",\n]/.test(escaped) ? `"${escaped}"` : escaped;
}

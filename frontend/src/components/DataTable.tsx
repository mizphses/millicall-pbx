import { type ReactNode, useCallback, useMemo, useState } from "react";
import { css, cx } from "../../styled-system/css";

interface Column<T> {
  header: string;
  accessor: (row: T) => ReactNode;
  /** Return a sortable primitive for this column. If omitted, column is not sortable. */
  sortValue?: (row: T) => string | number;
  className?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  emptyMessage?: string;
  emptyAction?: ReactNode;
}

type SortDir = "asc" | "desc";

const thBase = css({
  paddingInline: "14px",
  paddingBlock: "10px",
  textAlign: "left",
  fontSize: "11px",
  fontWeight: 600,
  color: "#8e8e96",
  textTransform: "uppercase",
  letterSpacing: "0.03em",
  background: "#faf9f7",
  borderBottom: "1px solid",
  borderColor: "#d4d2cd",
  whiteSpace: "nowrap",
  userSelect: "none",
});

const thSortable = css({
  cursor: "pointer",
  position: "relative",
  paddingRight: "22px",
  _hover: { color: "#4a4a52" },
});

const sortIcon = (dir: SortDir | null) =>
  css({
    position: "absolute",
    right: "6px",
    top: "50%",
    transform: "translateY(-50%)",
    fontSize: "10px",
    opacity: dir ? 0.8 : 0.3,
    _after: {
      content: dir === "asc" ? '"▲"' : dir === "desc" ? '"▼"' : '"⇅"',
    },
  });

export function DataTable<T>({
  columns,
  data,
  emptyMessage = "データがありません",
  emptyAction,
}: DataTableProps<T>) {
  const [sortCol, setSortCol] = useState<number | null>(null);
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  const handleSort = useCallback(
    (colIdx: number) => {
      if (sortCol === colIdx) {
        setSortDir((d) => (d === "asc" ? "desc" : "asc"));
      } else {
        setSortCol(colIdx);
        setSortDir("asc");
      }
    },
    [sortCol],
  );

  const sortedData = useMemo(() => {
    if (sortCol === null) return data;
    const col = columns[sortCol];
    if (!col?.sortValue) return data;
    const fn = col.sortValue;
    return [...data].sort((a, b) => {
      const av = fn(a);
      const bv = fn(b);
      let cmp: number;
      if (typeof av === "number" && typeof bv === "number") {
        cmp = av - bv;
      } else {
        cmp = String(av).localeCompare(String(bv), "ja");
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [data, columns, sortCol, sortDir]);

  if (data.length === 0) {
    return (
      <div
        className={css({
          background: "#ffffff",
          border: "1px solid #d4d2cd",
          borderRadius: "5px",
          padding: "48px",
          textAlign: "center",
          color: "#4a4a52",
        })}
      >
        <p className={css({ marginBottom: "12px" })}>{emptyMessage}</p>
        {emptyAction}
      </div>
    );
  }

  return (
    <div
      className={css({
        background: "#ffffff",
        border: "1px solid #d4d2cd",
        borderRadius: "5px",
        overflowX: "auto",
      })}
    >
      <table className={css({ width: "100%", borderCollapse: "collapse", fontSize: "13px" })}>
        <thead>
          <tr>
            {columns.map((col, i) => {
              const isSortable = !!col.sortValue;
              const isActive = sortCol === i;
              return (
                <th
                  key={`th-${i}`}
                  className={cx(thBase, isSortable ? thSortable : "", col.className ?? "")}
                  onClick={isSortable ? () => handleSort(i) : undefined}
                >
                  {col.header}
                  {isSortable && <span className={sortIcon(isActive ? sortDir : null)} />}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {sortedData.map((row, ri) => (
            <tr key={`row-${ri}`} className={css({ _hover: { background: "#fdf3ee" } })}>
              {columns.map((col, ci) => (
                <td
                  key={`cell-${ri}-${ci}`}
                  className={cx(
                    css({
                      paddingInline: "14px",
                      paddingBlock: "10px",
                      borderBottom: "1px solid #e6e4e0",
                      verticalAlign: "middle",
                    }),
                    col.className ?? "",
                  )}
                >
                  {col.accessor(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

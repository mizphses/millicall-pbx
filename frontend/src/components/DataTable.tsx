import type { ReactNode } from "react";
import { css, cx } from "../../styled-system/css";

interface Column<T> {
  header: string;
  accessor: (row: T) => ReactNode;
  className?: string;
  sortable?: boolean;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  emptyMessage?: string;
  emptyAction?: ReactNode;
}

export function DataTable<T>({
  columns,
  data,
  emptyMessage = "データがありません",
  emptyAction,
}: DataTableProps<T>) {
  if (data.length === 0) {
    return (
      <div
        className={css({
          background: "#ffffff",
          border: "1px solid",
          borderColor: "#d4d2cd",
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
        border: "1px solid",
        borderColor: "#d4d2cd",
        borderRadius: "5px",
        overflowX: "auto",
      })}
    >
      <table className={css({ width: "100%", borderCollapse: "collapse", fontSize: "13px" })}>
        <thead>
          <tr>
            {columns.map((col, i) => (
              <th
                key={i}
                className={cx(
                  css({
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
                  }),
                  col.className ?? "",
                )}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, ri) => (
            <tr key={ri} className={css({ _hover: { background: "#fdf3ee" } })}>
              {columns.map((col, ci) => (
                <td
                  key={ci}
                  className={cx(
                    css({
                      paddingInline: "14px",
                      paddingBlock: "10px",
                      borderBottom: "1px solid",
                      borderColor: "#e6e4e0",
                      verticalAlign: "middle",
                      _last: { borderBottom: "0" },
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

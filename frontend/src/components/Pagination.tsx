import { css } from "../../styled-system/css";

interface PaginationProps {
  total: number;
  limit: number;
  offset: number;
  onPageChange: (offset: number) => void;
}

const btnStyle = css({
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  minWidth: "32px",
  height: "32px",
  padding: "0 8px",
  fontSize: "13px",
  fontWeight: 500,
  borderRadius: "5px",
  border: "1px solid #d4d2cd",
  background: "#ffffff",
  color: "#1b1b1f",
  cursor: "pointer",
  _hover: { background: "#e6e4e0" },
  _disabled: { opacity: 0.4, cursor: "default", _hover: { background: "#ffffff" } },
});

const btnActive = css({
  background: "#c45d2c",
  color: "#ffffff",
  borderColor: "#c45d2c",
  _hover: { background: "#a84e24" },
});

export function Pagination({ total, limit, offset, onPageChange }: PaginationProps) {
  if (total <= limit) return null;

  const totalPages = Math.ceil(total / limit);
  const currentPage = Math.floor(offset / limit);

  const pages: number[] = [];
  for (let i = 0; i < totalPages; i++) {
    if (i === 0 || i === totalPages - 1 || Math.abs(i - currentPage) <= 2) {
      pages.push(i);
    }
  }

  // Add ellipsis markers
  const display: (number | "...")[] = [];
  for (let i = 0; i < pages.length; i++) {
    if (i > 0 && pages[i] - pages[i - 1] > 1) {
      display.push("...");
    }
    display.push(pages[i]);
  }

  return (
    <div
      className={css({
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        marginTop: "16px",
        gap: "8px",
        flexWrap: "wrap",
      })}
    >
      <span className={css({ fontSize: "13px", color: "#4a4a52" })}>
        {total}件中 {offset + 1}-{Math.min(offset + limit, total)}件
      </span>
      <div className={css({ display: "flex", gap: "4px" })}>
        <button
          type="button"
          className={btnStyle}
          disabled={currentPage === 0}
          onClick={() => onPageChange(Math.max(0, offset - limit))}
        >
          ‹
        </button>
        {display.map((item, i) =>
          item === "..." ? (
            <span key={`ellipsis-${i}`} className={css({ padding: "0 4px", color: "#8e8e96" })}>
              ...
            </span>
          ) : (
            <button
              key={`page-${item}`}
              type="button"
              className={`${btnStyle} ${item === currentPage ? btnActive : ""}`}
              onClick={() => onPageChange(item * limit)}
            >
              {item + 1}
            </button>
          ),
        )}
        <button
          type="button"
          className={btnStyle}
          disabled={currentPage >= totalPages - 1}
          onClick={() => onPageChange(offset + limit)}
        >
          ›
        </button>
      </div>
    </div>
  );
}

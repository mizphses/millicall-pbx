import { type ReactNode, useEffect } from "react";
import { css } from "../../styled-system/css";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}

export function Modal({ open, onClose, title, children }: ModalProps) {
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className={css({
        position: "fixed",
        inset: "0",
        background: "rgba(0,0,0,0.45)",
        zIndex: 200,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      })}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className={css({
          background: "#ffffff",
          borderRadius: "6px",
          shadow: "2xl",
          width: "90%",
          maxWidth: "640px",
          maxHeight: "80vh",
          overflowY: "auto",
          padding: "24px",
        })}
      >
        <div
          className={css({
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            marginBottom: "16px",
          })}
        >
          <h2 className={css({ fontSize: "15px", fontWeight: 600 })}>{title}</h2>
          <button
            onClick={onClose}
            className={css({
              fontSize: "20px",
              color: "#4a4a52",
              lineHeight: 1,
              cursor: "pointer",
              _hover: { color: "#1b1b1f" },
            })}
          >
            &times;
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

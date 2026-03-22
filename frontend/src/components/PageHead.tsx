import type { ReactNode } from "react";
import { css } from "../../styled-system/css";

interface PageHeadProps {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}

export function PageHead({ title, subtitle, actions }: PageHeadProps) {
  return (
    <div
      className={css({
        display: "flex",
        flexDirection: "column",
        gap: "16px",
        marginBottom: "20px",
        smDown: { flexDirection: "column" },
        sm: {
          flexDirection: "row",
          alignItems: "center",
          justifyContent: "space-between",
        },
      })}
    >
      <div>
        <h1
          className={css({
            fontSize: "21px",
            fontWeight: 700,
            letterSpacing: "-0.02em",
          })}
        >
          {title}
        </h1>
        {subtitle && <p className={css({ fontSize: "13px", color: "#4a4a52" })}>{subtitle}</p>}
      </div>
      {actions && <div className={css({ display: "flex", gap: "8px" })}>{actions}</div>}
    </div>
  );
}

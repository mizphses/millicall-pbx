import type { QueryClient } from "@tanstack/react-query";
import { createRootRouteWithContext, Link, Outlet, useRouter } from "@tanstack/react-router";
import { useState } from "react";
import { css } from "../../styled-system/css";
import { useAuth } from "../lib/auth";

interface RouterContext {
  auth: ReturnType<typeof useAuth>;
  queryClient: QueryClient;
}

export const Route = createRootRouteWithContext<RouterContext>()({
  component: RootLayout,
});

const navLinks = [
  { to: "/", label: "ホーム" },
  { to: "/extensions", label: "内線アカウント" },
  { to: "/peers", label: "SIP電話機登録" },
  { to: "/trunks", label: "外線トランク" },
  { to: "/devices", label: "デバイス管理" },
  { to: "/contacts", label: "電話帳" },
  { to: "/cdr", label: "発着信記録" },
  { to: "/call-history", label: "AI通話履歴" },
  { to: "/ondemand-calls", label: "オンデマンド" },
  { to: "/settings", label: "詳細設定" },
  { to: "/users", label: "管理者" },
] as const;

const navLinkBase = css({
  display: "flex",
  alignItems: "center",
  padding: "12px 14px",
  height: "auto",
  fontSize: "13px",
  fontWeight: 500,
  color: "#b0afc0",
  textDecoration: "none",
  borderBottom: "0",
  borderLeft: "3px solid transparent",
  whiteSpace: "nowrap",
  transition: "color 0.15s",
  md: {
    padding: "0 14px",
    height: "100%",
    borderBottom: "2px solid transparent",
    borderLeft: "0",
  },
  _hover: {
    color: "#ddd",
    background: "rgba(255,255,255,0.06)",
    md: { background: "transparent" },
  },
});

const navLinkActive = css({
  color: "#ffffff",
  borderLeftColor: "#c45d2c",
  background: "rgba(255,255,255,0.04)",
  md: {
    borderBottomColor: "#c45d2c",
    borderLeftColor: "transparent",
    background: "transparent",
  },
});

function RootLayout() {
  const [menuOpen, setMenuOpen] = useState(false);
  const router = useRouter();
  const auth = useAuth();
  const isLoginPage = router.state.location.pathname === "/login";

  return (
    <>
      <nav
        className={css({
          background: "#262630",
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          padding: "0",
          height: "auto",
          position: "sticky",
          top: "0",
          zIndex: 100,
          md: { padding: "0 20px", height: "48px" },
        })}
      >
        <Link
          to="/"
          className={css({
            fontWeight: 700,
            fontSize: "15px",
            color: "#ffffff",
            textDecoration: "none",
            paddingRight: "24px",
            marginRight: "4px",
            borderRight: "1px solid rgba(255,255,255,0.1)",
            letterSpacing: "-0.02em",
            padding: "12px 16px",
            md: { padding: "0" },
          })}
        >
          Millicall
        </Link>

        <button
          type="button"
          className={css({
            display: "block",
            background: "transparent",
            border: "none",
            color: "#b0afc0",
            cursor: "pointer",
            padding: "8px",
            marginLeft: "auto",
            marginRight: "12px",
            md: { display: "none" },
          })}
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label="メニュー"
        >
          <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <rect y="3" width="20" height="2" rx="1" />
            <rect y="9" width="20" height="2" rx="1" />
            <rect y="15" width="20" height="2" rx="1" />
          </svg>
        </button>

        {!isLoginPage && (
          <div
            className={css({
              display: menuOpen ? "flex" : "none",
              flexDirection: "column",
              width: "100%",
              height: "auto",
              borderTop: "1px solid rgba(255,255,255,0.08)",
              overflowX: "auto",
              md: {
                display: "flex",
                flexDirection: "row",
                width: "auto",
                height: "100%",
                borderTop: "0",
              },
            })}
          >
            {navLinks.map((link) => (
              <Link
                key={link.to}
                to={link.to}
                onClick={() => setMenuOpen(false)}
                className={navLinkBase}
                activeProps={{ className: navLinkActive }}
                activeOptions={{ exact: link.to === "/" }}
              >
                {link.label}
              </Link>
            ))}

            {auth.isAuthenticated && (
              <button
                type="button"
                onClick={() => {
                  auth.logout();
                  setMenuOpen(false);
                }}
                className={css({
                  display: "flex",
                  alignItems: "center",
                  padding: "12px 14px",
                  height: "auto",
                  fontSize: "13px",
                  fontWeight: 500,
                  color: "#b0afc0",
                  textDecoration: "none",
                  border: "none",
                  background: "transparent",
                  whiteSpace: "nowrap",
                  cursor: "pointer",
                  marginLeft: "auto",
                  _hover: { color: "#ddd" },
                  md: { padding: "0 14px", height: "100%" },
                })}
              >
                ログアウト
              </button>
            )}
          </div>
        )}
      </nav>

      <main
        className={css({
          maxWidth: "920px",
          marginLeft: "auto",
          marginRight: "auto",
          padding: "28px 24px 48px",
        })}
      >
        <Outlet />
      </main>

      <footer
        className={css({
          textAlign: "center",
          padding: "24px",
          fontSize: "11px",
          color: "#8e8e96",
        })}
      >
        Millicall PBX v0.1.0
      </footer>
    </>
  );
}

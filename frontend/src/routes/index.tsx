import { useQuery } from "@tanstack/react-query";
import { createFileRoute, Link, redirect } from "@tanstack/react-router";
import { css } from "../../styled-system/css";
import { PageHead } from "../components/PageHead";
import { api } from "../lib/api";

export const Route = createFileRoute("/")({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated) {
      throw redirect({ to: "/login" });
    }
  },
  component: Dashboard,
});

interface DashboardData {
  extensions: number;
  peers: number;
  trunks: number;
  devices: number;
}

const btnPrimary = css({
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  paddingInline: "14px",
  paddingBlock: "6px",
  fontSize: "13px",
  fontWeight: 500,
  borderRadius: "5px",
  background: "#c45d2c",
  color: "#ffffff",
  textDecoration: "none",
  _hover: { background: "#a84e24" },
});

const btnSecondary = css({
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  paddingInline: "14px",
  paddingBlock: "6px",
  fontSize: "13px",
  fontWeight: 500,
  borderRadius: "5px",
  background: "#ffffff",
  color: "#1b1b1f",
  border: "1px solid",
  borderColor: "#d4d2cd",
  textDecoration: "none",
  _hover: { background: "#e6e4e0" },
});

function Dashboard() {
  const { data, isLoading } = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => api.get<DashboardData>("/dashboard"),
  });

  if (isLoading || !data) {
    return <p className={css({ color: "#4a4a52" })}>読み込み中...</p>;
  }

  return (
    <>
      <PageHead title="ダッシュボード" subtitle="システムの概要" />

      <div
        className={css({
          display: "grid",
          gridTemplateColumns: "repeat(2, 1fr)",
          gap: "12px",
          marginBottom: "28px",
          sm: { gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))" },
        })}
      >
        <StatCard num={data.extensions ?? 0} label="内線アカウント" />
        <StatCard num={data.peers ?? 0} label="SIP電話機" />
        <StatCard num={data.trunks ?? 0} label="外線トランク" />
        <StatCard num={data.devices ?? 0} label="接続デバイス" />
      </div>

      <div className={css({ marginTop: "24px" })}>
        <h2 className={css({ fontSize: "15px", fontWeight: 600, marginBottom: "8px" })}>
          クイック操作
        </h2>
        <div className={css({ display: "flex", flexWrap: "wrap", gap: "8px" })}>
          <Link to="/extensions/new" className={btnPrimary}>
            内線アカウントを追加
          </Link>
          <Link to="/peers/new" className={btnSecondary}>
            SIP電話機を登録
          </Link>
          <Link to="/devices" className={btnSecondary}>
            デバイス管理
          </Link>
        </div>
      </div>
    </>
  );
}

function StatCard({ num, label }: { num: number; label: string }) {
  return (
    <div
      className={css({
        background: "#ffffff",
        border: "1px solid",
        borderColor: "#d4d2cd",
        borderRadius: "5px",
        padding: "14px",
        borderLeft: "3px solid",
        borderLeftColor: "#c45d2c",
      })}
    >
      <div
        className={css({
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: "26px",
          fontWeight: 500,
          lineHeight: 1,
        })}
      >
        {num}
      </div>
      <div className={css({ fontSize: "12px", color: "#4a4a52", marginTop: "4px" })}>{label}</div>
    </div>
  );
}

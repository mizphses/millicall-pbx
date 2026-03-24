import { createFileRoute, Link, redirect } from "@tanstack/react-router";
import { useState } from "react";
import { css } from "../../styled-system/css";
import { DataTable } from "../components/DataTable";
import { DialGuideModal } from "../components/DialGuideModal";
import { PageHead } from "../components/PageHead";
import { Tag } from "../components/Tag";
import { $api } from "../lib/client";

export const Route = createFileRoute("/trunks")({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated) throw redirect({ to: "/login" });
  },
  component: TrunksPage,
});

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
  cursor: "pointer",
  _hover: { background: "#e6e4e0" },
});

const btnEdit = css({
  display: "inline-flex",
  alignItems: "center",
  paddingInline: "10px",
  paddingBlock: "4px",
  fontSize: "12px",
  fontWeight: 500,
  borderRadius: "5px",
  background: "transparent",
  color: "#4a4a52",
  textDecoration: "none",
  _hover: { background: "#e6e4e0" },
});

const btnDelete = css({
  display: "inline-flex",
  alignItems: "center",
  paddingInline: "10px",
  paddingBlock: "4px",
  fontSize: "12px",
  fontWeight: 500,
  borderRadius: "5px",
  background: "transparent",
  color: "#b83232",
  border: "1px solid",
  borderColor: "#d4d2cd",
  cursor: "pointer",
  _hover: { background: "#fce8e8", borderColor: "#b83232" },
});

const codeStyle = css({
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: "12px",
  background: "#e6e4e0",
  paddingInline: "6px",
  paddingBlock: "2px",
  borderRadius: "3px",
});

function TrunksPage() {
  const [guideOpen, setGuideOpen] = useState(false);

  const { data: trunks, isLoading } = $api.useQuery("get", "/api/trunks");

  const deleteMutation = $api.useMutation("delete", "/api/trunks/{trunk_id}", {
    onSuccess: () => window.location.reload(),
  });

  const trunkList = trunks ?? [];

  if (isLoading) return <p className={css({ color: "#4a4a52" })}>読み込み中...</p>;

  return (
    <>
      <PageHead
        title="外線トランク"
        subtitle="PSTN接続（SIPトランク）を管理します"
        actions={
          <div className={css({ display: "flex", gap: "8px" })}>
            {trunkList.length > 0 && (
              <button type="button" onClick={() => setGuideOpen(true)} className={btnSecondary}>
                ダイヤルガイド
              </button>
            )}
            <Link to="/trunks/new" className={btnPrimary}>
              追加
            </Link>
          </div>
        }
      />

      <DataTable
        columns={[
          {
            header: "表示名",
            accessor: (t) => <strong>{t.display_name}</strong>,
          },
          {
            header: "名前（slug）",
            accessor: (t) => <code className={codeStyle}>{t.name}</code>,
          },
          {
            header: "ホスト",
            accessor: (t) => <code className={codeStyle}>{t.host}</code>,
          },
          {
            header: "電話番号",
            accessor: (t) => t.did_number || "-",
          },
          {
            header: "プレフィックス",
            accessor: (t) =>
              t.outbound_prefixes ? (
                <span className={css({ display: "flex", flexWrap: "wrap", gap: "4px" })}>
                  {t.outbound_prefixes.split(",").map((pfx, i) => (
                    <code key={i} className={codeStyle}>
                      {pfx.trim()}
                    </code>
                  ))}
                </span>
              ) : (
                <span className={css({ color: "#8e8e96" })}>0発信</span>
              ),
          },
          {
            header: "着信先",
            accessor: (t) => t.incoming_dest || "全内線",
          },
          {
            header: "状態",
            accessor: (t) =>
              t.enabled ? <Tag variant="ok">有効</Tag> : <Tag variant="ng">無効</Tag>,
          },
          {
            header: "",
            className: css({ textAlign: "right", whiteSpace: "nowrap" }),
            accessor: (t) => (
              <div className={css({ display: "flex", justifyContent: "flex-end", gap: "4px" })}>
                <Link
                  to="/trunks/$trunkId/edit"
                  params={{ trunkId: String(t.id) }}
                  className={btnEdit}
                >
                  編集
                </Link>
                <button
                  type="button"
                  onClick={() => {
                    if (confirm(`外線 ${t.display_name} を削除しますか？`))
                      deleteMutation.mutate({ params: { path: { trunk_id: t.id } } });
                  }}
                  className={btnDelete}
                >
                  削除
                </button>
              </div>
            ),
          },
        ]}
        data={trunkList}
        emptyMessage="外線トランクがまだ登録されていません"
        emptyAction={
          <Link to="/trunks/new" className={btnPrimary}>
            登録する
          </Link>
        }
      />

      <DialGuideModal open={guideOpen} onClose={() => setGuideOpen(false)} trunks={trunkList} />
    </>
  );
}

import { useQueryClient } from "@tanstack/react-query";
import { createFileRoute, redirect } from "@tanstack/react-router";
import { useState } from "react";
import { css } from "../../styled-system/css";
import { DataTable } from "../components/DataTable";
import { FormGroup, inputClass } from "../components/FormCard";
import { PageHead } from "../components/PageHead";
import { Tag } from "../components/Tag";
import { $api } from "../lib/client";

export const Route = createFileRoute("/ondemand-calls")({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated) throw redirect({ to: "/login" });
  },
  component: OnDemandCallsPage,
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
  border: "none",
  cursor: "pointer",
  _hover: { background: "#a84e24" },
});

const btnOutline = css({
  display: "inline-flex",
  alignItems: "center",
  paddingInline: "14px",
  paddingBlock: "6px",
  fontSize: "13px",
  fontWeight: 500,
  borderRadius: "5px",
  background: "#ffffff",
  color: "#1b1b1f",
  border: "1px solid #d4d2cd",
  cursor: "pointer",
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
  border: "1px solid #d4d2cd",
  cursor: "pointer",
  _hover: { background: "#fce8e8", borderColor: "#b83232" },
});

const btnCopy = css({
  display: "inline-flex",
  alignItems: "center",
  paddingInline: "10px",
  paddingBlock: "4px",
  fontSize: "12px",
  fontWeight: 500,
  borderRadius: "5px",
  background: "transparent",
  color: "#365a8a",
  border: "1px solid #d4d2cd",
  cursor: "pointer",
  _hover: { background: "#e8f0fc", borderColor: "#365a8a" },
});

function OnDemandCallsPage() {
  const queryClient = useQueryClient();
  const { data: entries, isLoading } = $api.useQuery("get", "/api/ondemand-calls");

  const [showForm, setShowForm] = useState(false);
  const [label, setLabel] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [copied, setCopied] = useState<number | null>(null);

  const createMutation = $api.useMutation("post", "/api/ondemand-calls", {
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["get", "/api/ondemand-calls"] });
      setLabel("");
      setPhoneNumber("");
      setShowForm(false);
    },
  });

  const deleteMutation = $api.useMutation("delete", "/api/ondemand-calls/{call_id}", {
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["get", "/api/ondemand-calls"] });
    },
  });

  function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    createMutation.mutate({
      body: { label, phone_number: phoneNumber, enabled: true },
    });
  }

  function handleDelete(id: number) {
    if (!confirm("削除しますか？")) return;
    deleteMutation.mutate({ params: { path: { call_id: id } } });
  }

  function copyUrl(id: number) {
    const url = `${window.location.origin}/ondemandcall/${id}`;
    navigator.clipboard.writeText(url);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  }

  if (isLoading) return <p className={css({ color: "#4a4a52" })}>読み込み中...</p>;

  return (
    <>
      <PageHead
        title="オンデマンドコール"
        subtitle="認証不要のワンクリック発信リンクを管理します"
        actions={
          <button type="button" className={btnPrimary} onClick={() => setShowForm(true)}>
            新規作成
          </button>
        }
      />

      {showForm && (
        <div
          className={css({
            background: "#ffffff",
            border: "1px solid #d4d2cd",
            borderRadius: "5px",
            padding: "20px",
            marginBottom: "16px",
          })}
        >
          <form onSubmit={handleCreate}>
            <div className={css({ display: "flex", gap: "16px", flexWrap: "wrap" })}>
              <FormGroup label="ラベル" >
                <input
                  type="text"
                  className={inputClass}
                  value={label}
                  onChange={(e) => setLabel(e.target.value)}
                  placeholder="例: 受付呼び出し"
                  required
                />
              </FormGroup>
              <FormGroup label="電話番号" >
                <input
                  type="text"
                  className={inputClass}
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  placeholder="例: 800"
                  required
                />
              </FormGroup>
            </div>
            <div className={css({ display: "flex", gap: "8px", marginTop: "12px" })}>
              <button type="submit" className={btnPrimary} disabled={createMutation.isPending}>
                {createMutation.isPending ? "作成中..." : "作成"}
              </button>
              <button type="button" className={btnOutline} onClick={() => setShowForm(false)}>
                キャンセル
              </button>
            </div>
          </form>
        </div>
      )}

      <DataTable
        columns={[
          {
            header: "ID",
            sortValue: (e) => e.id ?? 0,
            accessor: (e) => (
              <strong className={css({ fontFamily: "'JetBrains Mono', monospace", fontSize: "13px" })}>
                {e.id}
              </strong>
            ),
          },
          { header: "ラベル", sortValue: (e) => e.label, accessor: (e) => e.label },
          {
            header: "電話番号",
            accessor: (e) => (
              <span className={css({ fontFamily: "'JetBrains Mono', monospace" })}>{e.phone_number}</span>
            ),
          },
          {
            header: "状態",
            accessor: (e) =>
              e.enabled ? <Tag variant="ok">有効</Tag> : <Tag variant="ng">無効</Tag>,
          },
          {
            header: "URL",
            accessor: (e) => (
              <div className={css({ display: "flex", alignItems: "center", gap: "4px" })}>
                <code
                  className={css({
                    fontSize: "11px",
                    color: "#4a4a52",
                    background: "#f0eeeb",
                    padding: "2px 6px",
                    borderRadius: "3px",
                  })}
                >
                  /ondemandcall/{e.id}
                </code>
                <button type="button" className={btnCopy} onClick={() => e.id && copyUrl(e.id)}>
                  {copied === e.id ? "コピー済" : "コピー"}
                </button>
              </div>
            ),
          },
          {
            header: "",
            className: css({ textAlign: "right" }),
            accessor: (e) => (
              <button type="button" className={btnDelete} onClick={() => e.id && handleDelete(e.id)}>
                削除
              </button>
            ),
          },
        ]}
        data={entries ?? []}
        emptyMessage="オンデマンドコールが登録されていません"
        emptyAction={
          <button type="button" className={btnPrimary} onClick={() => setShowForm(true)}>
            作成する
          </button>
        }
      />
    </>
  );
}

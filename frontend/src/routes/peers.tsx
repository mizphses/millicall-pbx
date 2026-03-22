import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, Link, redirect } from "@tanstack/react-router";
import { css } from "../../styled-system/css";
import { DataTable } from "../components/DataTable";
import { PageHead } from "../components/PageHead";
import { Tag } from "../components/Tag";
import { api } from "../lib/api";

export const Route = createFileRoute("/peers")({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated) throw redirect({ to: "/login" });
  },
  component: PeersPage,
});

interface Peer {
  id: number;
  username: string;
  transport: string;
  codecs: string[];
  ip_address: string | null;
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

function PeersPage() {
  const queryClient = useQueryClient();
  const { data: peers = [], isLoading } = useQuery({
    queryKey: ["peers"],
    queryFn: () => api.get<Peer[]>("/peers"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/peers/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["peers"] }),
  });

  if (isLoading) return <p className={css({ color: "#4a4a52" })}>読み込み中...</p>;

  return (
    <>
      <PageHead
        title="SIP電話機登録"
        subtitle="SIPエンドポイントの認証アカウントを管理します"
        actions={
          <Link to="/peers/new" className={btnPrimary}>
            追加
          </Link>
        }
      />

      <DataTable
        columns={[
          {
            header: "ユーザー名",
            accessor: (peer) => <strong>{peer.username}</strong>,
          },
          {
            header: "トランスポート",
            accessor: (peer) => <Tag variant="muted">{peer.transport.toUpperCase()}</Tag>,
          },
          {
            header: "コーデック",
            accessor: (peer) => (Array.isArray(peer.codecs) ? peer.codecs.join(", ") : peer.codecs),
          },
          {
            header: "IPアドレス",
            accessor: (peer) => peer.ip_address || "動的",
          },
          {
            header: "",
            className: css({ textAlign: "right", whiteSpace: "nowrap" }),
            accessor: (peer) => (
              <div className={css({ display: "flex", justifyContent: "flex-end", gap: "4px" })}>
                <Link
                  to="/peers/$peerId/edit"
                  params={{ peerId: String(peer.id) }}
                  className={btnEdit}
                >
                  編集
                </Link>
                <button
                  onClick={() => {
                    if (confirm(`SIPピア ${peer.username} を削除しますか？`))
                      deleteMutation.mutate(peer.id);
                  }}
                  className={btnDelete}
                >
                  削除
                </button>
              </div>
            ),
          },
        ]}
        data={peers}
        emptyMessage="SIP電話機がまだ登録されていません"
        emptyAction={
          <Link to="/peers/new" className={btnPrimary}>
            登録する
          </Link>
        }
      />
    </>
  );
}

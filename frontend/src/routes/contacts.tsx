import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, Link, redirect } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { css } from "../../styled-system/css";
import { DataTable } from "../components/DataTable";
import { PageHead } from "../components/PageHead";
import { api } from "../lib/api";

export const Route = createFileRoute("/contacts")({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated) throw redirect({ to: "/login" });
  },
  component: ContactsPage,
});

interface Contact {
  id: number;
  name: string;
  phone_number: string;
  company: string | null;
  department: string | null;
  notes: string | null;
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

const searchInput = css({
  width: "100%",
  maxWidth: "360px",
  paddingInline: "10px",
  paddingBlock: "8px",
  fontSize: "14px",
  color: "#1b1b1f",
  background: "#ffffff",
  border: "1px solid",
  borderColor: "#d4d2cd",
  borderRadius: "5px",
  outline: "none",
  marginBottom: "16px",
  _focus: { borderColor: "#c45d2c", ringWidth: "2", ringColor: "rgba(196, 93, 44, 0.12)" },
});

function ContactsPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");

  const { data: contacts = [], isLoading } = useQuery({
    queryKey: ["contacts"],
    queryFn: () => api.get<Contact[]>("/contacts"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/contacts/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["contacts"] }),
  });

  const filtered = useMemo(() => {
    if (!search.trim()) return contacts;
    const q = search.toLowerCase();
    return contacts.filter(
      (c) =>
        c.name.toLowerCase().includes(q) ||
        c.phone_number.toLowerCase().includes(q) ||
        c.company?.toLowerCase().includes(q) ||
        c.department?.toLowerCase().includes(q) ||
        c.notes?.toLowerCase().includes(q),
    );
  }, [contacts, search]);

  if (isLoading) return <p className={css({ color: "#4a4a52" })}>読み込み中...</p>;

  return (
    <>
      <PageHead
        title="電話帳"
        subtitle="連絡先を管理します"
        actions={
          <Link to="/contacts/new" className={btnPrimary}>
            追加
          </Link>
        }
      />

      <input
        type="text"
        className={searchInput}
        placeholder="名前・電話番号・会社名で検索..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />

      <DataTable
        columns={[
          {
            header: "名前",
            accessor: (c) => <strong>{c.name}</strong>,
            sortValue: (c) => c.name,
          },
          {
            header: "電話番号",
            accessor: (c) => c.phone_number,
            sortValue: (c) => c.phone_number,
          },
          {
            header: "会社",
            accessor: (c) => c.company || "-",
            sortValue: (c) => c.company || "",
          },
          {
            header: "部署",
            accessor: (c) => c.department || "-",
            sortValue: (c) => c.department || "",
          },
          {
            header: "メモ",
            accessor: (c) =>
              c.notes ? (c.notes.length > 30 ? `${c.notes.slice(0, 30)}...` : c.notes) : "-",
            sortValue: (c) => c.notes || "",
          },
          {
            header: "",
            className: css({ textAlign: "right", whiteSpace: "nowrap" }),
            accessor: (c) => (
              <div className={css({ display: "flex", justifyContent: "flex-end", gap: "4px" })}>
                <Link
                  to="/contacts/$contactId/edit"
                  params={{ contactId: String(c.id) }}
                  className={btnEdit}
                >
                  編集
                </Link>
                <button
                  type="button"
                  onClick={() => {
                    if (confirm(`${c.name} を削除しますか？`)) deleteMutation.mutate(c.id);
                  }}
                  className={btnDelete}
                >
                  削除
                </button>
              </div>
            ),
          },
        ]}
        data={filtered}
        emptyMessage="連絡先がまだ登録されていません"
        emptyAction={
          <Link to="/contacts/new" className={btnPrimary}>
            登録する
          </Link>
        }
      />
    </>
  );
}

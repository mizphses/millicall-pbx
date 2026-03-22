import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, redirect } from "@tanstack/react-router";
import { type FormEvent, useState } from "react";
import { css } from "../../styled-system/css";
import { DataTable } from "../components/DataTable";
import { FormGroup, inputClass, selectClass } from "../components/FormCard";
import { PageHead } from "../components/PageHead";
import { Tag } from "../components/Tag";
import { api } from "../lib/api";

export const Route = createFileRoute("/users")({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated) throw redirect({ to: "/login" });
  },
  component: UsersPage,
});

interface User {
  id: number;
  username: string;
  display_name: string;
  is_admin: boolean;
}

const cardStyle = css({
  background: "#ffffff",
  border: "1px solid #d4d2cd",
  borderRadius: "6px",
  padding: "20px",
  marginBottom: "20px",
});

const btnPrimary = css({
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  paddingInline: "14px",
  paddingBlock: "8px",
  fontSize: "13px",
  fontWeight: 500,
  borderRadius: "5px",
  background: "#c45d2c",
  color: "#ffffff",
  border: "none",
  cursor: "pointer",
  _hover: { background: "#a84e24" },
  _disabled: { opacity: 0.5 },
});

const btnOutline = css({
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  paddingInline: "10px",
  paddingBlock: "5px",
  fontSize: "12px",
  fontWeight: 500,
  borderRadius: "4px",
  background: "#ffffff",
  color: "#1b1b1f",
  border: "1px solid #d4d2cd",
  cursor: "pointer",
  _hover: { background: "#e6e4e0" },
});

const btnDanger = css({
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  paddingInline: "10px",
  paddingBlock: "5px",
  fontSize: "12px",
  fontWeight: 500,
  borderRadius: "4px",
  background: "transparent",
  color: "#b83232",
  border: "1px solid #d4d2cd",
  cursor: "pointer",
  _hover: { background: "#fce8e8", borderColor: "#b83232" },
});

function UsersPage() {
  const queryClient = useQueryClient();
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [passwordTarget, setPasswordTarget] = useState<User | null>(null);

  const { data: users = [], isLoading } = useQuery({
    queryKey: ["users"],
    queryFn: () => api.get<User[]>("/users"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/users/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["users"] }),
    onError: (err: Error) => alert(err.message),
  });

  if (isLoading) return <p className={css({ color: "#4a4a52" })}>...</p>;

  return (
    <>
      <PageHead
        title="管理者アカウント"
        subtitle="ログインユーザーの管理"
        actions={
          <button type="button" className={btnPrimary} onClick={() => setShowCreateForm(true)}>
            + 新規ユーザー
          </button>
        }
      />

      {showCreateForm && (
        <CreateUserForm
          onClose={() => setShowCreateForm(false)}
          onCreated={() => {
            setShowCreateForm(false);
            queryClient.invalidateQueries({ queryKey: ["users"] });
          }}
        />
      )}

      {editingUser && (
        <EditUserForm
          user={editingUser}
          onClose={() => setEditingUser(null)}
          onUpdated={() => {
            setEditingUser(null);
            queryClient.invalidateQueries({ queryKey: ["users"] });
          }}
        />
      )}

      {passwordTarget && (
        <ChangePasswordForm user={passwordTarget} onClose={() => setPasswordTarget(null)} />
      )}

      <DataTable
        columns={[
          { header: "ID", accessor: (u) => u.id },
          { header: "ユーザー名", accessor: (u) => u.username },
          { header: "表示名", accessor: (u) => u.display_name },
          {
            header: "権限",
            accessor: (u) =>
              u.is_admin ? <Tag variant="ok">管理者</Tag> : <Tag variant="muted">一般</Tag>,
          },
          {
            header: "",
            accessor: (u) => (
              <div className={css({ display: "flex", gap: "6px" })}>
                <button type="button" className={btnOutline} onClick={() => setEditingUser(u)}>
                  編集
                </button>
                <button type="button" className={btnOutline} onClick={() => setPasswordTarget(u)}>
                  PW変更
                </button>
                <button
                  type="button"
                  className={btnDanger}
                  onClick={() => {
                    if (confirm(`${u.username} を削除しますか？`)) deleteMutation.mutate(u.id);
                  }}
                >
                  削除
                </button>
              </div>
            ),
          },
        ]}
        data={users}
        emptyMessage="ユーザーがいません"
      />
    </>
  );
}

function CreateUserForm({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [isAdmin, setIsAdmin] = useState(false);
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: () =>
      api.post("/users", {
        username,
        password,
        display_name: displayName,
        is_admin: isAdmin,
      }),
    onSuccess: onCreated,
    onError: (err: Error) => setError(err.message),
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    mutation.mutate();
  }

  return (
    <div className={cardStyle}>
      <h3 className={css({ fontSize: "15px", fontWeight: 600, marginBottom: "16px" })}>
        新規ユーザー作成
      </h3>
      {error && (
        <p className={css({ color: "#b83232", fontSize: "13px", marginBottom: "12px" })}>{error}</p>
      )}
      <form onSubmit={handleSubmit}>
        <div className={css({ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" })}>
          <FormGroup label="ユーザー名">
            <input
              className={inputClass}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </FormGroup>
          <FormGroup label="パスワード">
            <input
              className={inputClass}
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={4}
            />
          </FormGroup>
          <FormGroup label="表示名">
            <input
              className={inputClass}
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              required
            />
          </FormGroup>
          <FormGroup label="権限">
            <select
              className={selectClass}
              value={isAdmin ? "admin" : "user"}
              onChange={(e) => setIsAdmin(e.target.value === "admin")}
            >
              <option value="user">一般</option>
              <option value="admin">管理者</option>
            </select>
          </FormGroup>
        </div>
        <div className={css({ display: "flex", gap: "8px", marginTop: "16px" })}>
          <button type="submit" className={btnPrimary} disabled={mutation.isPending}>
            {mutation.isPending ? "作成中..." : "作成"}
          </button>
          <button type="button" className={btnOutline} onClick={onClose}>
            キャンセル
          </button>
        </div>
      </form>
    </div>
  );
}

function EditUserForm({
  user,
  onClose,
  onUpdated,
}: {
  user: User;
  onClose: () => void;
  onUpdated: () => void;
}) {
  const [displayName, setDisplayName] = useState(user.display_name);
  const [isAdmin, setIsAdmin] = useState(user.is_admin);
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: () =>
      api.put(`/users/${user.id}`, { display_name: displayName, is_admin: isAdmin }),
    onSuccess: onUpdated,
    onError: (err: Error) => setError(err.message),
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    mutation.mutate();
  }

  return (
    <div className={cardStyle}>
      <h3 className={css({ fontSize: "15px", fontWeight: 600, marginBottom: "16px" })}>
        {user.username} を編集
      </h3>
      {error && (
        <p className={css({ color: "#b83232", fontSize: "13px", marginBottom: "12px" })}>{error}</p>
      )}
      <form onSubmit={handleSubmit}>
        <div className={css({ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" })}>
          <FormGroup label="表示名">
            <input
              className={inputClass}
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              required
            />
          </FormGroup>
          <FormGroup label="権限">
            <select
              className={selectClass}
              value={isAdmin ? "admin" : "user"}
              onChange={(e) => setIsAdmin(e.target.value === "admin")}
            >
              <option value="user">一般</option>
              <option value="admin">管理者</option>
            </select>
          </FormGroup>
        </div>
        <div className={css({ display: "flex", gap: "8px", marginTop: "16px" })}>
          <button type="submit" className={btnPrimary} disabled={mutation.isPending}>
            {mutation.isPending ? "保存中..." : "保存"}
          </button>
          <button type="button" className={btnOutline} onClick={onClose}>
            キャンセル
          </button>
        </div>
      </form>
    </div>
  );
}

function ChangePasswordForm({ user, onClose }: { user: User; onClose: () => void }) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  const mutation = useMutation({
    mutationFn: () =>
      api.put(`/users/${user.id}/password`, {
        current_password: currentPassword,
        new_password: newPassword,
      }),
    onSuccess: () => setDone(true),
    onError: (err: Error) => setError(err.message),
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    mutation.mutate();
  }

  if (done) {
    return (
      <div className={cardStyle}>
        <p className={css({ color: "#2a7e4f", fontSize: "14px", marginBottom: "12px" })}>
          {user.username} のパスワードを変更しました
        </p>
        <button type="button" className={btnOutline} onClick={onClose}>
          閉じる
        </button>
      </div>
    );
  }

  return (
    <div className={cardStyle}>
      <h3 className={css({ fontSize: "15px", fontWeight: 600, marginBottom: "16px" })}>
        {user.username} のパスワード変更
      </h3>
      {error && (
        <p className={css({ color: "#b83232", fontSize: "13px", marginBottom: "12px" })}>{error}</p>
      )}
      <form onSubmit={handleSubmit}>
        <div className={css({ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" })}>
          <FormGroup label="現在のパスワード（自分 or 管理者）">
            <input
              className={inputClass}
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              required
            />
          </FormGroup>
          <FormGroup label="新しいパスワード">
            <input
              className={inputClass}
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              minLength={4}
            />
          </FormGroup>
        </div>
        <div className={css({ display: "flex", gap: "8px", marginTop: "16px" })}>
          <button type="submit" className={btnPrimary} disabled={mutation.isPending}>
            {mutation.isPending ? "変更中..." : "変更"}
          </button>
          <button type="button" className={btnOutline} onClick={onClose}>
            キャンセル
          </button>
        </div>
      </form>
    </div>
  );
}

import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { css } from "../../styled-system/css";
import { inputClass } from "../components/FormCard";
import { useAuth } from "../lib/auth";

export const Route = createFileRoute("/login")({
  component: LoginPage,
});

function LoginPage() {
  const auth = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await auth.login(username, password);
      navigate({ to: "/" });
    } catch {
      setError("ユーザー名またはパスワードが正しくありません");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={css({ maxWidth: "sm", marginInline: "auto", marginTop: "80px" })}>
      <h1
        className={css({
          fontSize: "21px",
          fontWeight: 700,
          letterSpacing: "-0.02em",
          marginBottom: "4px",
        })}
      >
        ログイン
      </h1>
      <p className={css({ fontSize: "13px", color: "#4a4a52", marginBottom: "20px" })}>
        Millicall PBXの管理画面にログインします
      </p>

      <div
        className={css({
          background: "#ffffff",
          border: "1px solid",
          borderColor: "#d4d2cd",
          borderRadius: "5px",
          padding: "20px",
        })}
      >
        <form onSubmit={handleSubmit}>
          {error && (
            <div
              className={css({
                background: "#fce8e8",
                color: "#b83232",
                fontSize: "13px",
                paddingInline: "12px",
                paddingBlock: "8px",
                borderRadius: "5px",
                marginBottom: "16px",
              })}
            >
              {error}
            </div>
          )}

          <div className={css({ marginBottom: "16px" })}>
            <label
              className={css({
                display: "block",
                fontSize: "13px",
                fontWeight: 500,
                marginBottom: "4px",
              })}
            >
              ユーザー名
            </label>
            <input
              type="text"
              className={inputClass}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </div>

          <div className={css({ marginBottom: "16px" })}>
            <label
              className={css({
                display: "block",
                fontSize: "13px",
                fontWeight: 500,
                marginBottom: "4px",
              })}
            >
              パスワード
            </label>
            <input
              type="password"
              className={inputClass}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className={css({
              width: "100%",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              paddingInline: "18px",
              paddingBlock: "10px",
              fontSize: "14px",
              fontWeight: 500,
              borderRadius: "5px",
              background: "#c45d2c",
              color: "#ffffff",
              minHeight: "38px",
              cursor: "pointer",
              _hover: { background: "#a84e24" },
              _disabled: { opacity: "0.5" },
            })}
          >
            {loading ? "ログイン中..." : "ログイン"}
          </button>
        </form>
      </div>
    </div>
  );
}

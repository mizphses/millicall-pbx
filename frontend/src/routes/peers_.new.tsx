import { useQueryClient } from "@tanstack/react-query";
import { createFileRoute, redirect, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import {
  FormCard,
  FormGroup,
  FormRow,
  FormSection,
  inputClass,
  selectClass,
} from "../components/FormCard";
import { PageHead } from "../components/PageHead";
import { $api } from "../lib/client";

export const Route = createFileRoute("/peers_/new")({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated) throw redirect({ to: "/login" });
  },
  component: PeerNewPage,
});

function PeerNewPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [transport, setTransport] = useState("udp");
  const [codecs, setCodecs] = useState("ulaw, alaw");
  const [ipAddress, setIpAddress] = useState("");

  const mutation = $api.useMutation("post", "/api/peers", {
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["get", "/api/peers"] });
      navigate({ to: "/peers" });
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    mutation.mutate({
      body: {
        username,
        password,
        transport,
        codecs: codecs
          .split(",")
          .map((c) => c.trim())
          .filter(Boolean),
        ip_address: ipAddress || null,
      },
    });
  }

  return (
    <>
      <PageHead title="SIP電話機を登録" />
      <FormCard
        onSubmit={handleSubmit}
        submitLabel="作成"
        cancelHref="/peers"
        isSubmitting={mutation.isPending}
      >
        <FormSection title="認証情報" />
        <FormRow>
          <FormGroup label="ユーザー名">
            <input
              type="text"
              className={inputClass}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="phone01"
              required
            />
          </FormGroup>
          <FormGroup label="パスワード">
            <input
              type="password"
              className={inputClass}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="パスワード"
              required
            />
          </FormGroup>
        </FormRow>

        <FormSection title="接続設定" />
        <FormRow>
          <FormGroup label="トランスポート">
            <select
              className={selectClass}
              value={transport}
              onChange={(e) => setTransport(e.target.value)}
            >
              <option value="udp">UDP</option>
              <option value="tcp">TCP</option>
            </select>
          </FormGroup>
          <FormGroup label="コーデック" hint="カンマ区切り（例: ulaw, alaw）">
            <input
              type="text"
              className={inputClass}
              value={codecs}
              onChange={(e) => setCodecs(e.target.value)}
            />
          </FormGroup>
        </FormRow>

        <FormGroup label="IPアドレス" hint="空欄の場合は動的（どのIPからでも接続可）">
          <input
            type="text"
            className={inputClass}
            value={ipAddress}
            onChange={(e) => setIpAddress(e.target.value)}
            placeholder="192.168.1.100"
          />
        </FormGroup>
      </FormCard>
    </>
  );
}

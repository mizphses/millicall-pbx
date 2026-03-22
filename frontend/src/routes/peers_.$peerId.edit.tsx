import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, redirect, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { css } from "../../styled-system/css";
import {
  FormCard,
  FormGroup,
  FormRow,
  FormSection,
  inputClass,
  selectClass,
} from "../components/FormCard";
import { PageHead } from "../components/PageHead";
import { api } from "../lib/api";

export const Route = createFileRoute("/peers_/$peerId/edit")({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated) throw redirect({ to: "/login" });
  },
  component: PeerEditPage,
});

interface Peer {
  id: number;
  username: string;
  password: string;
  transport: string;
  codecs: string[];
  ip_address: string | null;
}

function PeerEditPage() {
  const { peerId } = Route.useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: peer } = useQuery({
    queryKey: ["peer", peerId],
    queryFn: () => api.get<Peer>(`/peers/${peerId}`),
  });

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [transport, setTransport] = useState("udp");
  const [codecs, setCodecs] = useState("ulaw, alaw");
  const [ipAddress, setIpAddress] = useState("");

  useEffect(() => {
    if (peer) {
      setUsername(peer.username);
      setPassword(peer.password);
      setTransport(peer.transport);
      setCodecs(Array.isArray(peer.codecs) ? peer.codecs.join(", ") : peer.codecs);
      setIpAddress(peer.ip_address || "");
    }
  }, [peer]);

  const mutation = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.put(`/peers/${peerId}`, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["peers"] });
      queryClient.invalidateQueries({ queryKey: ["peer", peerId] });
      navigate({ to: "/peers" });
    },
  });

  if (!peer) return <p className={css({ color: "#4a4a52" })}>読み込み中...</p>;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    mutation.mutate({
      username,
      password,
      transport,
      codecs: codecs
        .split(",")
        .map((c) => c.trim())
        .filter(Boolean),
      ip_address: ipAddress || null,
    });
  }

  return (
    <>
      <PageHead title="SIP電話機を編集" />
      <FormCard
        onSubmit={handleSubmit}
        submitLabel="更新"
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
              required
            />
          </FormGroup>
          <FormGroup label="パスワード">
            <input
              type="password"
              className={inputClass}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
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

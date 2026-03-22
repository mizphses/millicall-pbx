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
  textareaClass,
} from "../components/FormCard";
import { PageHead } from "../components/PageHead";
import { api } from "../lib/api";

export const Route = createFileRoute("/extensions_/$extensionId/edit")({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated) throw redirect({ to: "/login" });
  },
  component: ExtensionEditPage,
});

interface Extension {
  id: number;
  number: string;
  display_name: string;
  type: string;
  enabled: boolean;
  peer_id: number | null;
  ai_agent_id: number | null;
}

interface Agent {
  id: number;
  name: string;
  greeting_text: string;
  system_prompt: string;
  llm_provider: string;
  llm_model: string;
  max_history: number;
  tts_provider: string;
  coefont_voice_id: string;
  google_tts_voice: string;
}

interface Peer {
  id: number;
  username: string;
}

const checkboxLabel = css({
  display: "inline-flex",
  alignItems: "center",
  gap: "8px",
  fontSize: "14px",
  cursor: "pointer",
  paddingBlock: "4px",
});

const checkboxInput = css({
  width: "16px",
  height: "16px",
  accentColor: "#c45d2c",
});

function ExtensionEditPage() {
  const { extensionId } = Route.useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: ext } = useQuery({
    queryKey: ["extension", extensionId],
    queryFn: () => api.get<Extension>(`/extensions/${extensionId}`),
  });

  const { data: agent } = useQuery({
    queryKey: ["agent", ext?.ai_agent_id],
    queryFn: () => api.get<Agent>(`/agents/${ext!.ai_agent_id}`),
    enabled: !!ext && ext.type === "ai_agent" && !!ext.ai_agent_id,
  });

  const { data: peers = [] } = useQuery({
    queryKey: ["peers"],
    queryFn: () => api.get<Peer[]>("/peers"),
  });

  const [number, setNumber] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [peerId, setPeerId] = useState("");
  const [enabled, setEnabled] = useState(true);
  const [greetingText, setGreetingText] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [llmProvider, setLlmProvider] = useState("google");
  const [llmModel, setLlmModel] = useState("gemini-2.5-flash");
  const [maxHistory, setMaxHistory] = useState(10);
  const [ttsProvider, setTtsProvider] = useState("coefont");
  const [coefontVoiceId, setCoefontVoiceId] = useState("");
  const [googleTtsVoice, setGoogleTtsVoice] = useState("ja-JP-Chirp3-HD-Aoede");

  useEffect(() => {
    if (ext) {
      setNumber(ext.number);
      setDisplayName(ext.display_name);
      setPeerId(ext.peer_id ? String(ext.peer_id) : "");
      setEnabled(ext.enabled);
    }
  }, [ext]);

  useEffect(() => {
    if (agent) {
      setGreetingText(agent.greeting_text);
      setSystemPrompt(agent.system_prompt);
      setLlmProvider(agent.llm_provider);
      setLlmModel(agent.llm_model);
      setMaxHistory(agent.max_history);
      setTtsProvider(agent.tts_provider);
      setCoefontVoiceId(agent.coefont_voice_id);
      setGoogleTtsVoice(agent.google_tts_voice);
    }
  }, [agent]);

  const mutation = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.put(`/extensions/${extensionId}`, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["extensions"] });
      queryClient.invalidateQueries({ queryKey: ["extension", extensionId] });
      navigate({ to: "/extensions" });
    },
  });

  const llmDefaults: Record<string, string> = {
    google: "gemini-2.5-flash",
    openai: "gpt-4o-mini",
    anthropic: "claude-sonnet-4-20250514",
  };

  if (!ext) return <p className={css({ color: "#4a4a52" })}>読み込み中...</p>;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const body: Record<string, unknown> = {
      type: ext!.type,
      number,
      display_name: displayName,
      enabled,
    };

    if (ext!.type === "phone") {
      body.peer_id = peerId ? parseInt(peerId, 10) : null;
    } else {
      body.greeting_text = greetingText;
      body.system_prompt = systemPrompt;
      body.llm_provider = llmProvider;
      body.llm_model = llmModel;
      body.max_history = maxHistory;
      body.tts_provider = ttsProvider;
      body.coefont_voice_id = coefontVoiceId;
      body.google_tts_voice = googleTtsVoice;
    }

    mutation.mutate(body);
  }

  if (ext.type === "phone") {
    return (
      <>
        <PageHead title="内線アカウントを編集" />
        <FormCard
          onSubmit={handleSubmit}
          submitLabel="更新"
          cancelHref="/extensions"
          isSubmitting={mutation.isPending}
        >
          <FormSection title="基本情報" />
          <FormRow>
            <FormGroup label="内線番号">
              <input
                type="text"
                className={inputClass}
                value={number}
                onChange={(e) => setNumber(e.target.value)}
                required
                pattern="\d+"
              />
            </FormGroup>
            <FormGroup label="表示名">
              <input
                type="text"
                className={inputClass}
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                required
              />
            </FormGroup>
          </FormRow>

          <FormSection title="接続先SIPピア" />
          <FormGroup label="SIPピア" hint="この内線番号にかかってきたときに鳴らすSIP電話機">
            <select
              className={selectClass}
              value={peerId}
              onChange={(e) => setPeerId(e.target.value)}
            >
              <option value="">-- 未割当 --</option>
              {peers.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.username}
                </option>
              ))}
            </select>
          </FormGroup>

          <label className={checkboxLabel}>
            <input
              type="checkbox"
              className={checkboxInput}
              checked={enabled}
              onChange={(e) => setEnabled(e.target.checked)}
            />
            この内線を有効にする
          </label>
        </FormCard>
      </>
    );
  }

  return (
    <>
      <PageHead title="内線アカウントを編集" />
      <FormCard
        onSubmit={handleSubmit}
        submitLabel="更新"
        cancelHref="/extensions"
        isSubmitting={mutation.isPending}
      >
        <FormSection title="基本情報" />
        <FormRow>
          <FormGroup label="エージェント名">
            <input
              type="text"
              className={inputClass}
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              required
            />
          </FormGroup>
          <FormGroup label="内線番号" hint="この番号にダイヤルするとAIが応答します">
            <input
              type="text"
              className={inputClass}
              value={number}
              onChange={(e) => setNumber(e.target.value)}
              required
              pattern="\d+"
            />
          </FormGroup>
        </FormRow>

        <FormGroup label="挨拶メッセージ" hint="AIが電話に出たとき最初に話す言葉">
          <input
            type="text"
            className={inputClass}
            value={greetingText}
            onChange={(e) => setGreetingText(e.target.value)}
          />
        </FormGroup>

        <label className={checkboxLabel}>
          <input
            type="checkbox"
            className={checkboxInput}
            checked={enabled}
            onChange={(e) => setEnabled(e.target.checked)}
          />
          このエージェントを有効にする
        </label>

        <FormSection title="システムプロンプト" />
        <FormGroup label="プロンプト">
          <textarea
            className={textareaClass}
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
            rows={8}
          />
        </FormGroup>

        <FormSection title="LLM設定" />
        <FormRow>
          <FormGroup label="プロバイダー">
            <select
              className={selectClass}
              value={llmProvider}
              onChange={(e) => {
                setLlmProvider(e.target.value);
                setLlmModel(llmDefaults[e.target.value] || "");
              }}
            >
              <option value="google">Google Gemini</option>
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic Claude</option>
            </select>
          </FormGroup>
          <FormGroup label="モデル名">
            <input
              type="text"
              className={inputClass}
              value={llmModel}
              onChange={(e) => setLlmModel(e.target.value)}
            />
          </FormGroup>
        </FormRow>
        <FormGroup label="会話履歴のターン数">
          <input
            type="number"
            className={`${css({ maxWidth: "100px" })} ${inputClass}`}
            value={maxHistory}
            onChange={(e) => setMaxHistory(parseInt(e.target.value, 10))}
            min={2}
            max={50}
          />
        </FormGroup>

        <FormSection title="音声合成（TTS）" />
        <FormGroup label="TTSプロバイダー">
          <select
            className={selectClass}
            value={ttsProvider}
            onChange={(e) => setTtsProvider(e.target.value)}
          >
            <option value="coefont">CoeFont</option>
            <option value="google">Google Chirp3 HD</option>
          </select>
        </FormGroup>

        {ttsProvider === "coefont" ? (
          <FormGroup label="CoeFont ボイスID">
            <input
              type="text"
              className={inputClass}
              value={coefontVoiceId}
              onChange={(e) => setCoefontVoiceId(e.target.value)}
            />
          </FormGroup>
        ) : (
          <FormGroup label="Google Chirp3 ボイス">
            <select
              className={selectClass}
              value={googleTtsVoice}
              onChange={(e) => setGoogleTtsVoice(e.target.value)}
            >
              <option value="ja-JP-Chirp3-HD-Aoede">Aoede（女性）</option>
              <option value="ja-JP-Chirp3-HD-Kore">Kore（女性）</option>
              <option value="ja-JP-Chirp3-HD-Leda">Leda（女性）</option>
              <option value="ja-JP-Chirp3-HD-Zephyr">Zephyr（女性）</option>
              <option value="ja-JP-Chirp3-HD-Charon">Charon（男性）</option>
              <option value="ja-JP-Chirp3-HD-Fenrir">Fenrir（男性）</option>
              <option value="ja-JP-Chirp3-HD-Orus">Orus（男性）</option>
              <option value="ja-JP-Chirp3-HD-Puck">Puck（男性）</option>
            </select>
          </FormGroup>
        )}
      </FormCard>
    </>
  );
}

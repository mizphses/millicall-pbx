import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, redirect, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
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

export const Route = createFileRoute("/extensions_/new")({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated) throw redirect({ to: "/login" });
  },
  component: ExtensionNewPage,
});

interface Peer {
  id: number;
  username: string;
}

const tabBtn = (active: boolean) =>
  css({
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    paddingInline: "14px",
    paddingBlock: "6px",
    fontSize: "13px",
    fontWeight: 500,
    borderRadius: "5px",
    cursor: "pointer",
    background: active ? "#c45d2c" : "#ffffff",
    color: active ? "#ffffff" : "#1b1b1f",
    border: active ? "none" : "1px solid",
    borderColor: active ? undefined : "#d4d2cd",
    _hover: active ? undefined : { background: "#e6e4e0" },
  });

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

function ExtensionNewPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [type, setType] = useState<"phone" | "ai_agent">("phone");
  const [number, setNumber] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [peerId, setPeerId] = useState("");
  const [enabled, setEnabled] = useState(true);

  // AI agent fields
  const [greetingText, setGreetingText] = useState("お電話ありがとうございます。ご用件をどうぞ。");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [llmProvider, setLlmProvider] = useState("google");
  const [llmModel, setLlmModel] = useState("gemini-2.5-flash");
  const [maxHistory, setMaxHistory] = useState(10);
  const [ttsProvider, setTtsProvider] = useState("coefont");
  const [coefontVoiceId, setCoefontVoiceId] = useState("cbe4e152-40a5-4c0d-91cd-2fc27d60e6bd");
  const [googleTtsVoice, setGoogleTtsVoice] = useState("ja-JP-Chirp3-HD-Aoede");

  const { data: peers = [] } = useQuery({
    queryKey: ["peers"],
    queryFn: () => api.get<Peer[]>("/peers"),
  });

  const mutation = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post("/extensions", body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["extensions"] });
      navigate({ to: "/extensions" });
    },
  });

  const llmDefaults: Record<string, string> = {
    google: "gemini-2.5-flash",
    openai: "gpt-4o-mini",
    anthropic: "claude-sonnet-4-20250514",
  };

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const body: Record<string, unknown> = {
      type,
      number,
      display_name: displayName,
      enabled,
    };

    if (type === "phone") {
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

  return (
    <>
      <PageHead title="内線アカウントを追加" />

      <div className={css({ display: "flex", gap: "8px", marginBottom: "20px" })}>
        <button type="button" onClick={() => setType("phone")} className={tabBtn(type === "phone")}>
          電話番号
        </button>
        <button
          type="button"
          onClick={() => setType("ai_agent")}
          className={tabBtn(type === "ai_agent")}
        >
          AIエージェント
        </button>
      </div>

      {type === "phone" ? (
        <FormCard
          onSubmit={handleSubmit}
          submitLabel="作成"
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
                placeholder="1001"
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
                placeholder="受付"
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
      ) : (
        <FormCard
          onSubmit={handleSubmit}
          submitLabel="作成"
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
                placeholder="受付AI"
                required
              />
            </FormGroup>
            <FormGroup label="内線番号" hint="この番号にダイヤルするとAIが応答します">
              <input
                type="text"
                className={inputClass}
                value={number}
                onChange={(e) => setNumber(e.target.value)}
                placeholder="9000"
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
              placeholder="お電話ありがとうございます。"
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
              placeholder="システムプロンプトを入力..."
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
      )}
    </>
  );
}

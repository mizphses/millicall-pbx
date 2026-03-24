---
title: 環境変数
description: .env ファイルの設定項目一覧
---

Millicall PBX の設定は `.env` ファイルで管理します。`.env` がない場合でも起動は可能ですが、シークレットが毎回ランダム生成されるため、本番では必ず設定してください。

## 生成方法

```bash
# CLI で対話式生成
millicall setup

# スクリプトで一括生成
bash scripts/generate-env.sh

# 手動でコピー
cp .env.example .env
```

## 必須項目

| 変数 | 説明 | デフォルト |
|------|------|-----------|
| `JWT_SECRET` | JWT トークンの署名キー。64文字以上推奨 | 自動生成 (警告あり) |
| `ADMIN_PASSWORD` | 初期管理者 (`admin`) のパスワード | 自動生成 (ログ出力) |
| `ARI_PASSWORD` | Asterisk REST Interface のパスワード | 自動生成 |
| `ARI_USER` | ARI のユーザー名 | `millicall` |

## ネットワーク設定

| 変数 | 説明 | デフォルト |
|------|------|-----------|
| `PBX_BIND_ADDRESS` | Asterisk のバインドアドレス | `0.0.0.0` |
| `WEB_HOST` | API サーバーのバインドアドレス | `0.0.0.0` |
| `WEB_PORT` | API サーバーのポート | `8000` |

## LLM API キー

AI 電話応対やワークフローの AI ノードを使用する場合に設定します。WebUI の「詳細設定」からも変更可能です。

| 変数 | 用途 |
|------|------|
| `GOOGLE_API_KEY` | Gemini (LLM, TTS) |
| `OPENAI_API_KEY` | Whisper (STT), GPT (LLM) |
| `ANTHROPIC_API_KEY` | Claude (LLM) |

## TTS (音声合成)

| 変数 | 説明 |
|------|------|
| `COEFONT_ACCESS_KEY` | CoeFont のアクセスキー |
| `COEFONT_ACCESS_SECRET` | CoeFont のシークレット |
| `COEFONT_VOICE_ID` | デフォルトの音声ID |

## Cloudflare Tunnel

| 変数 | 説明 |
|------|------|
| `CLOUDFLARE_TUNNEL_TOKEN` | Tunnel トークン ([取得方法](/millicall-pbx/setup/tunnel/)) |

## シークレットの生成

個別にシークレットを生成する場合:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

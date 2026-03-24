---
title: 概要
description: Millicall PBX の機能と特徴
---

Millicall PBX は Docker で動く IP-PBX システムです。SIP 電話機の管理、AI を活用した電話応対ワークフロー、ブラウザからの WebRTC 通話に対応しています。

## 主な機能

- **内線管理** — SIP 電話機と内線番号の管理、自動プロビジョニング
- **AIワークフロー** — ビジュアルエディタで電話応対フローを設計。Gemini による自動生成にも対応
- **外線トランク** — SIP プロバイダーとの接続、着信ルーティング
- **WebRTC** — ブラウザ上でSIP通話（専用アプリ不要）
- **MCP サーバー** — Claude Desktop から電話の発信・連絡先管理が可能
- **CDR / 通話履歴** — 通話記録の閲覧、AI 通話のトランスクリプト確認

## 対応電話機

| メーカー | シリーズ | プロビジョニング |
|---------|---------|----------------|
| Panasonic | KX-HDVシリーズ | 自動 (HTTP) |
| Yealink | Tシリーズ | 自動 (HTTP) |
| 汎用SIP | - | 手動設定 |

## システム要件

- Docker Engine 24.0 以上
- Docker Compose v2 (Docker Desktop または plugin)
- Ubuntu 24.04 LTS 推奨（サーバー用途）
- macOS / Windows (Docker Desktop) でも動作

## 技術スタック

| レイヤー | 技術 |
|---------|------|
| PBX | Asterisk 20 |
| バックエンド | Python / FastAPI |
| フロントエンド | React / TanStack Router / Panda CSS |
| データベース | SQLite (aiosqlite) |
| AI | Google Gemini / OpenAI / Anthropic |
| TTS | Google Cloud TTS / CoeFont |
| STT | OpenAI Whisper |

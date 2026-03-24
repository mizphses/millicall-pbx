---
title: システム構成
description: Millicall PBX のアーキテクチャと Docker 構成
---

## 全体構成

```mermaid
graph TB
  subgraph "Docker Host"
    subgraph "host network"
      AST["Asterisk<br/>SIP/RTP"]
      API["FastAPI<br/>:8000"]
      ARI["ARI Listener<br/>WebSocket"]
    end
    subgraph "bridge network"
      NGX["nginx<br/>:80"]
      CF["cloudflared<br/>(optional)"]
    end
    DB[(SQLite)]
  end

  Phone["IP電話機"] -->|SIP/RTP| AST
  Browser["ブラウザ"] -->|HTTP| NGX
  NGX -->|proxy| API
  NGX -->|ws proxy| AST
  API --> DB
  ARI -->|WebSocket| AST
  CF -->|HTTP| NGX
  Internet["インターネット"] -->|Tunnel| CF
```

## コンテナ構成

| サービス | ネットワーク | 役割 |
|---------|------------|------|
| **millicall** | host | Asterisk + FastAPI + ARI listener を1コンテナで実行 |
| **frontend** | bridge (port 80) | nginx でReact SPAを配信、APIへのリバースプロキシ |
| **cloudflared** | bridge (optional) | Cloudflare Tunnel による外部アクセス |

### なぜ millicall は host network なのか

Asterisk は SIP (UDP 5060) と RTP (UDP 10000-10100) で大量の UDP ポートを使用します。Docker のブリッジネットワークでは NAT が介在し、SIP の NAT 越え問題が発生するため、Asterisk コンテナは `network_mode: host` で動作させています。

frontend と cloudflared は SIP/RTP を扱わないため、ブリッジネットワークでネットワーク分離しています。

## プロセス構成

millicall コンテナ内では3つのプロセスが動作します:

```mermaid
graph LR
  EP["entrypoint.sh<br/>(root)"] --> AST["Asterisk<br/>(root)"]
  EP --> UVICORN["uvicorn<br/>(millicall user)"]
  EP --> ARILS["ARI Listener<br/>(millicall user)"]
  UVICORN --> FASTAPI["FastAPI App"]
  ARILS --> WF["Workflow Executor"]
  ARILS --> AI["AI Call Handler"]
```

- **Asterisk** — root で実行（SIPポートのバインドに必要）
- **uvicorn (FastAPI)** — millicall ユーザーで実行（Web API）
- **ARI Listener** — millicall ユーザーで実行（通話イベントのハンドリング）

## データフロー

### 通常の電話通話

```mermaid
sequenceDiagram
  participant Phone as IP電話機
  participant AST as Asterisk
  participant Phone2 as 相手先
  Phone->>AST: INVITE (SIP)
  AST->>Phone2: INVITE (SIP)
  Phone2->>AST: 200 OK
  AST->>Phone: 200 OK
  Phone->>AST: RTP (音声)
  AST->>Phone2: RTP (音声)
```

### AI ワークフロー通話

```mermaid
sequenceDiagram
  participant Phone as 発信者
  participant AST as Asterisk
  participant ARI as ARI Listener
  participant WF as Workflow Executor
  participant STT as STT (Whisper)
  participant LLM as LLM (Gemini)
  participant TTS as TTS

  Phone->>AST: 着信
  AST->>ARI: StasisStart
  ARI->>WF: ワークフロー実行開始
  WF->>TTS: 挨拶テキスト
  TTS->>AST: 音声ファイル
  AST->>Phone: 挨拶再生
  Phone->>AST: 発話 (RTP)
  AST->>WF: 録音データ
  WF->>STT: 音声→テキスト
  STT->>WF: テキスト
  WF->>LLM: テキスト + プロンプト
  LLM->>WF: 応答テキスト
  WF->>TTS: 応答テキスト
  TTS->>AST: 音声ファイル
  AST->>Phone: 応答再生
```

## データベース

SQLite を使用。Docker volume `millicall-data` に永続化されます。

主なテーブル:

| テーブル | 内容 |
|---------|------|
| extensions | 内線番号 |
| peers | SIP ピア（電話機アカウント） |
| trunks | 外線トランク |
| devices | 電話機デバイス |
| workflows | ワークフロー定義 |
| contacts | 電話帳 |
| users | 管理ユーザー |
| settings | システム設定（APIキー等） |
| call_logs / call_messages | AI通話ログ |
| cdr_records | 通話詳細記録 |

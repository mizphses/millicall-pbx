# Millicall PBX — 初期セットアップガイド

## 前提条件

- Ubuntu 24.04 LTS サーバー (amd64)
- Docker Engine 24.0+
- IP電話機用の専用NIC (オプション、PoEスイッチ接続用)

## 1. サーバー準備

### 1.1 Docker のインストール

```bash
bash deploy/install-docker.sh
```

インストール後、再ログインして `docker` グループを反映:

```bash
newgrp docker
docker version
```

### 1.2 電話機ネットワークの設定 (オプション)

IP電話機を専用ネットワークで運用する場合:

```bash
sudo bash deploy/setup-host-network.sh
```

この設定で以下が構成されます:
- 専用NIC (`enp3s0`) に 172.20.0.1/16 を割り当て
- DHCP サーバー (dnsmasq) で電話機に自動IP付与
- NAT で電話機がインターネットにアクセス可能

> NIC名やIPレンジはお使いの環境に合わせて `setup-host-network.sh` を編集してください。

## 2. 環境変数の設定

### 2.1 自動生成 (推奨)

```bash
bash scripts/generate-env.sh
```

ランダムなシークレットが生成されます。出力された管理者パスワードを控えておいてください。

### 2.2 手動設定

```bash
cp .env.example .env
chmod 600 .env
```

`.env` を編集し、以下の必須項目を設定:

| 変数 | 説明 | 生成方法 |
|------|------|---------|
| `JWT_SECRET` | JWT署名シークレット (64文字以上推奨) | `python3 -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `ADMIN_PASSWORD` | 初期管理者パスワード | 任意の強いパスワード |
| `WEBRTC_PASSWORD` | WebRTC SIP認証パスワード | `python3 -c "import secrets; print(secrets.token_urlsafe(16))"` |
| `ARI_PASSWORD` | Asterisk REST Interface パスワード | `python3 -c "import secrets; print(secrets.token_urlsafe(16))"` |

### 2.3 LLM API キー (AI機能を使う場合)

AI電話応対やワークフローのAIノードを使用する場合、利用するプロバイダーのAPIキーを設定:

```env
GOOGLE_API_KEY=your-google-api-key
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
```

設定はWebUIの「設定」画面からも変更可能です。

## 3. ビルドと起動

```bash
docker compose build
docker compose up -d
```

起動確認:

```bash
# 全コンテナが running か確認
docker compose ps

# バックエンドのログ
docker logs millicall-pbx --tail 20

# "Millicall PBX started" が表示されれば成功
```

WebUI にアクセス: `http://<サーバーIP>/`

初回ログイン:
- ユーザー名: `admin`
- パスワード: `.env` の `ADMIN_PASSWORD` に設定した値

## 4. Cloudflare Tunnel (リモートアクセス)

外部からの安全なアクセスには Cloudflare Tunnel を使用します。

### 4.1 Tunnel の作成

1. [Cloudflare Zero Trust ダッシュボード](https://one.dash.cloudflare.com/) にログイン
2. **Networks** > **Tunnels** > **Create a tunnel**
3. **Cloudflared** を選択して tunnel 名を入力
4. 表示されたトークンをコピー

### 4.2 トークンの設定

`.env` に追加:

```env
CLOUDFLARE_TUNNEL_TOKEN=eyJ...（コピーしたトークン）
```

### 4.3 Public Hostname の設定

Cloudflare ダッシュボードの Tunnel 設定で Public Hostname を追加:

| 項目 | 値 |
|------|-----|
| Subdomain | 任意 (例: `pbx`) |
| Domain | お使いのドメイン |
| Type | HTTP |
| URL | `host.docker.internal:80` |

> **重要**: frontend コンテナはブリッジネットワークで動作するため、cloudflared から `localhost:80` ではアクセスできません。`host.docker.internal:80` を指定してください。Tunnel からホストのポート80を経由して frontend コンテナに到達します。

### 4.4 追加の Hostname (MCP用、オプション)

MCP (Model Context Protocol) を外部から利用する場合、同じ Tunnel に追加のルートは不要です。
すべてのパス (`/mcp`, `/.well-known/`, `/authorize`, `/token` 等) は同じポート80で nginx がプロキシします。

### 4.5 Access Policy (推奨)

Cloudflare Access で追加の認証を設定することを推奨します:

1. **Access** > **Applications** > **Add an application**
2. **Self-hosted** を選択
3. Application domain に Tunnel のドメインを設定
4. Policy でアクセスを許可するユーザーやメール認証を設定

これにより、Millicall のログイン画面に到達する前に Cloudflare の認証が挟まります。

### 4.6 起動

```bash
docker compose up -d cloudflared
docker logs millicall-tunnel
# "Connection ... registered" が表示されれば成功
```

## 5. ファイアウォール設定

`network_mode: host` を使用するため、ファイアウォールの設定は必須です。
詳細は [docs/firewall.md](firewall.md) を参照してください。

最低限:

```bash
# ARI を外部に公開しない
sudo iptables -A INPUT -p tcp --dport 8088 -j DROP
# API を外部に直接公開しない (nginx 経由のみ)
sudo iptables -A INPUT -p tcp --dport 8000 ! -s 127.0.0.1 -j DROP
```

## 6. IP電話機の接続

### 6.1 ピアの作成

WebUI > **ピア** > **新規作成** で SIP 認証情報を作成:
- ユーザー名: 任意 (例: `ext800`)
- パスワード: 自動生成推奨

### 6.2 内線の作成

WebUI > **内線** > **新規作成** で内線番号を割り当て:
- 番号: 任意 (例: `800`)
- ピア: 上で作成したピアを選択

### 6.3 デバイスの登録

WebUI > **デバイス** で電話機を登録すると、プロビジョニング設定が自動生成されます。
対応機種:
- Panasonic KX-HDVシリーズ
- Yealink Tシリーズ

電話機のプロビジョニングURLを以下に設定:
- Panasonic: `http://<PBX IP>:8000/provisioning/Panasonic/Config{MAC}.cfg`
- Yealink: `http://<PBX IP>:8000/provisioning/Yealink/{mac}.cfg`

## 7. トラブルシューティング

### コンテナが起動しない

```bash
docker compose logs --tail 50
```

### SIP 登録ができない

```bash
# Asterisk の SIP ステータス確認
docker exec millicall-pbx asterisk -rx 'pjsip show endpoints'
docker exec millicall-pbx asterisk -rx 'pjsip show registrations'
```

### 502 Bad Gateway

```bash
# バックエンドが起動しているか
docker exec millicall-pbx ps aux | grep uvicorn

# nginx から API に到達できるか
docker exec millicall-frontend curl -s -o /dev/null -w "%{http_code}" http://host.docker.internal:8000/api/auth/me
# 401 が返れば正常（認証が必要なだけ）
```

### Cloudflare Tunnel が繋がらない

```bash
docker logs millicall-tunnel --tail 20

# Tunnel の Service URL が host.docker.internal:80 になっているか確認
# Cloudflare ダッシュボード > Networks > Tunnels > 設定
```

### データベースエラー (readonly)

```bash
# パーミッション確認
docker exec millicall-pbx ls -la /app/data/

# 修正
docker exec millicall-pbx chown -R millicall:millicall /app/data
docker compose restart millicall
```

## 8. アップデート

```bash
# ローカルからデプロイ
bash deploy/deploy.sh

# または手動
git pull
docker compose build --no-cache
docker compose up -d
```

データは Docker volume (`millicall-data`) に永続化されるため、コンテナの再ビルドでデータは失われません。

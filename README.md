# Millicall PBX

Docker で動く IP-PBX。SIP 電話機の管理、AI 電話応対ワークフローに対応。

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/mizphses/millicall/main/install.sh | bash
```

対話形式でセットアップが完了し、自動で起動します。

## Manual Setup

```bash
git clone https://github.com/mizphses/millicall.git
cd millicall
docker compose up -d
```

初回は `.env` なしでも起動します。管理者パスワードはログに出力されます:

```bash
docker compose logs millicall 2>&1 | grep "ADMIN_PASSWORD"
```

### セキュリティとカスタマイズ

`.env` で以下の値を調整すると、公開環境でも安全に運用しつつフロントエンドやリバースプロキシ構成に合わせたチューニングができます。

| 変数 | 役割 |
|------|------|
| `ALLOWED_HOSTS` | FastAPI の `TrustedHostMiddleware` に渡すホスト許可リスト。Host ヘッダをホワイトリスト化して SSRF/Tunnel 経由の不正アクセスを防ぎます。 |
| `CORS_ALLOWED_ORIGINS` | API を利用できるオリジン一覧。Cloudflare Tunnel や独自フロントエンドを追加する場合はここに URL を追加します。 |
| `SESSION_COOKIE_NAME` / `SESSION_COOKIE_SAMESITE` / `SESSION_COOKIE_SECURE` | ログイン Cookie の名前と属性。`SESSION_COOKIE_SECURE` を空欄にすると自動判定 (HTTPS のみ secure) になり、強制したい場合は `true`/`false` を設定します。 |

`scripts/generate-env.sh` や `install.sh` はこれらのキーも含めて `.env` を生成するため、セットアップ直後から安全なデフォルトで動作します。

### CLI を使う場合

```bash
pip install -e .
millicall setup     # 対話式セットアップ
millicall start     # 起動 (tunnel 自動検出)
millicall stop      # 停止
millicall logs      # ログ
millicall status    # 状態確認
```

## 構成

```
millicall (host network)     Asterisk + FastAPI + ARI listener
frontend  (bridge, port 80)  nginx + React SPA
cloudflared (optional)       Cloudflare Tunnel
```

## ドキュメント

- [初期セットアップ詳細](docs/setup.md)
- [ファイアウォール設定](docs/firewall.md)

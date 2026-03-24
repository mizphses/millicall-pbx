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

---
title: ファイアウォール
description: ポート公開範囲とファイアウォール設定
---

Millicall の Asterisk コンテナは `network_mode: host` で動作するため、ポートがホストに直接露出します。本番環境では必ずファイアウォールを設定してください。

## ポート一覧

| ポート | プロトコル | 用途 | 公開範囲 |
|--------|-----------|------|---------|
| 80 | TCP | フロントエンド (nginx) | LAN / Tunnel 経由 |
| 5060 | UDP/TCP | SIP シグナリング | LAN のみ |
| 8000 | TCP | API サーバー | localhost のみ |
| 8088 | TCP | ARI WebSocket | **localhost のみ** |
| 10000-10100 | UDP | RTP メディア | LAN のみ |

## 公開してはいけないポート

- **8088 (ARI)** — Asterisk の管理 API。公開すると通話制御を乗っ取られます
- **8000 (API)** — nginx 経由でアクセスさせるべき。直接公開するとセキュリティヘッダーをバイパスされます

## iptables 設定例

```bash
# ポリシー
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT

# ループバック & established
iptables -A INPUT -i lo -j ACCEPT
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# SSH
iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# SIP (LAN のみ)
iptables -A INPUT -s 172.20.0.0/16 -p udp --dport 5060 -j ACCEPT
iptables -A INPUT -s 172.20.0.0/16 -p tcp --dport 5060 -j ACCEPT

# RTP (LAN のみ)
iptables -A INPUT -s 172.20.0.0/16 -p udp --dport 10000:10100 -j ACCEPT

# フロントエンド (LAN のみ)
iptables -A INPUT -s 172.20.0.0/16 -p tcp --dport 80 -j ACCEPT

# API — localhost のみ
iptables -A INPUT -s 127.0.0.1 -p tcp --dport 8000 -j ACCEPT

# ARI — localhost のみ
iptables -A INPUT -s 127.0.0.1 -p tcp --dport 8088 -j ACCEPT

# 永続化
netfilter-persistent save
```

## 確認方法

```bash
# 開いているポートの確認
sudo ss -tlnp
sudo ss -ulnp

# ファイアウォールルールの確認
sudo iptables -L -n -v
```

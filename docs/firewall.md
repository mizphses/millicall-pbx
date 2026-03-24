# Firewall Configuration

Millicall PBX は `network_mode: host` で動作するため、コンテナのポートがホストに直接露出します。
本番環境では必ずファイアウォールを設定し、必要なポートのみを許可してください。

## 必要なポート

| ポート | プロトコル | 用途 | 公開範囲 |
|--------|-----------|------|---------|
| 80 | TCP | フロントエンド (nginx) | LAN / Cloudflare Tunnel |
| 443 | TCP | HTTPS (将来) | LAN / Cloudflare Tunnel |
| 5060 | UDP/TCP | SIP シグナリング | LAN のみ |
| 8000 | TCP | API サーバー (FastAPI) | localhost / nginx proxy のみ |
| 8088 | TCP | ARI WebSocket | **localhost のみ** |
| 10000-10100 | UDP | RTP メディア | LAN のみ |

## 公開してはいけないポート

- **8088 (ARI)** — Asterisk の管理 API。外部に公開すると通話制御を乗っ取られます
- **8000 (API)** — nginx 経由でアクセスさせるべき。直接公開すると CORS やセキュリティヘッダーをバイパスされます

## nftables 設定例 (推奨)

```bash
#!/usr/sbin/nft -f
flush ruleset

table inet filter {
    chain input {
        type filter hook input priority 0; policy drop;

        # ループバックとestablished
        iif lo accept
        ct state established,related accept

        # ICMP
        ip protocol icmp accept
        ip6 nexthdr icmpv6 accept

        # SSH (管理用)
        tcp dport 22 accept

        # SIP (LAN: 172.20.0.0/16 のみ)
        ip saddr 172.20.0.0/16 udp dport 5060 accept
        ip saddr 172.20.0.0/16 tcp dport 5060 accept

        # RTP メディア (LAN のみ)
        ip saddr 172.20.0.0/16 udp dport 10000-10100 accept

        # フロントエンド (LAN のみ。Cloudflare Tunnel 経由で外部アクセス)
        ip saddr 172.20.0.0/16 tcp dport 80 accept

        # API — localhost のみ (nginx からプロキシ)
        ip saddr 127.0.0.1 tcp dport 8000 accept

        # ARI — localhost のみ
        ip saddr 127.0.0.1 tcp dport 8088 accept

        # DHCP (電話機用)
        ip saddr 172.20.0.0/16 udp dport 67 accept

        # ログして拒否
        log prefix "nft-drop: " drop
    }

    chain forward {
        type filter hook forward priority 0; policy drop;

        # 電話機ネットワーク → インターネット (NAT)
        iifname "enp3s0" oifname "wlp2s0" accept
        iifname "wlp2s0" oifname "enp3s0" ct state related,established accept
    }

    chain output {
        type filter hook output priority 0; policy accept;
    }
}
```

## iptables 設定例

nftables が利用できない環境向け:

```bash
#!/bin/bash
set -e

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

# DHCP
iptables -A INPUT -s 172.20.0.0/16 -p udp --dport 67 -j ACCEPT

# FORWARD (NAT)
iptables -A FORWARD -i enp3s0 -o wlp2s0 -j ACCEPT
iptables -A FORWARD -i wlp2s0 -o enp3s0 -m state --state RELATED,ESTABLISHED -j ACCEPT
iptables -t nat -A POSTROUTING -s 172.20.0.0/16 -o wlp2s0 -j MASQUERADE

# 永続化
netfilter-persistent save
```

## 適用手順

```bash
# nftables の場合
sudo cp docs/nftables.conf /etc/nftables.conf
sudo systemctl enable nftables
sudo systemctl restart nftables

# iptables の場合
sudo bash docs/iptables-setup.sh
```

## Cloudflare Tunnel 利用時

Cloudflare Tunnel (`cloudflared`) を使用している場合、外部からのHTTPアクセスは Tunnel 経由になるため:

- ポート 80/443 を外部に直接公開する必要はない
- `cloudflared` はホスト上の `localhost:80` に接続するため、ファイアウォールでは localhost からのアクセスも許可が必要
- Tunnel 側の Access Policy で追加の認証を設定することを推奨

```bash
# Cloudflare Tunnel 用: localhost からの HTTP も許可
iptables -A INPUT -s 127.0.0.1 -p tcp --dport 80 -j ACCEPT
```

## 確認方法

```bash
# 開いているポートの確認
sudo ss -tlnp
sudo ss -ulnp

# 外部からのポートスキャン (別マシンから)
nmap -sS -sU -p 22,80,5060,8000,8088 <PBXのIP>

# ファイアウォールルールの確認
sudo nft list ruleset      # nftables
sudo iptables -L -n -v     # iptables
```

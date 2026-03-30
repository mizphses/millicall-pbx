#!/bin/bash
# Host network setup for Millicall PBX
# Run this on the server BEFORE docker compose up
#
# Usage: sudo bash deploy/setup-host-network.sh [PHONE_IF] [WAN_IF]
#   PHONE_IF: NIC connected to phone network (default: enp3s0)
#   WAN_IF:   NIC connected to internet      (default: auto-detect)
set -e

PHONE_IF="${1:-enp3s0}"
WAN_IF="${2:-$(ip route show default | awk '{print $5}' | head -1)}"

if [ -z "$WAN_IF" ]; then
    echo "ERROR: Cannot detect WAN interface. Pass it as 2nd argument."
    exit 1
fi

echo "=== Millicall PBX Host Network Setup ==="
echo "  Phone NIC : $PHONE_IF"
echo "  WAN NIC   : $WAN_IF"
echo ""

# 1. Configure phone NIC with static IP
echo "[1/7] Configuring $PHONE_IF (172.20.0.1/16)..."
cat > /etc/netplan/60-millicall.yaml << EOF
network:
  version: 2
  ethernets:
    ${PHONE_IF}:
      addresses:
        - 172.20.0.1/16
      link-local: []
EOF
netplan apply
echo "  -> $PHONE_IF configured"

# 2. Enable IP forwarding
echo "[2/7] Enabling IP forwarding..."
cat > /etc/sysctl.d/99-millicall.conf << 'EOF'
net.ipv4.ip_forward=1
EOF
sysctl -p /etc/sysctl.d/99-millicall.conf
echo "  -> IP forwarding enabled"

# 3. NAT rules (phone network -> internet)
echo "[3/7] Setting up NAT (masquerade)..."
apt-get install -y iptables-persistent > /dev/null 2>&1 || true

iptables -t nat -C POSTROUTING -s 172.20.0.0/16 -o "$WAN_IF" -j MASQUERADE 2>/dev/null || \
    iptables -t nat -A POSTROUTING -s 172.20.0.0/16 -o "$WAN_IF" -j MASQUERADE

iptables -C FORWARD -i "$PHONE_IF" -o "$WAN_IF" -j ACCEPT 2>/dev/null || \
    iptables -A FORWARD -i "$PHONE_IF" -o "$WAN_IF" -j ACCEPT

iptables -C FORWARD -i "$WAN_IF" -o "$PHONE_IF" -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || \
    iptables -A FORWARD -i "$WAN_IF" -o "$PHONE_IF" -m state --state RELATED,ESTABLISHED -j ACCEPT

netfilter-persistent save
echo "  -> NAT rules configured"

# 4. DHCP server for phone network
echo "[4/7] Setting up DHCP (dnsmasq)..."
apt-get install -y dnsmasq > /dev/null 2>&1

cat > /etc/dnsmasq.d/millicall.conf << EOF
interface=${PHONE_IF}
bind-interfaces
dhcp-range=172.20.1.1,172.20.254.254,255.255.0.0,12h
dhcp-option=3,172.20.0.1
dhcp-option=6,172.20.0.1
dhcp-option=66,http://172.20.0.1:8000/provisioning/
EOF

systemctl restart dnsmasq
systemctl enable dnsmasq
echo "  -> DHCP server running on $PHONE_IF"

# 5. NTP server (chrony)
echo "[5/7] Setting up NTP server (chrony)..."
apt-get install -y chrony > /dev/null 2>&1

mkdir -p /etc/chrony/conf.d
cat > /etc/chrony/conf.d/millicall.conf << 'EOF'
server ntp.nict.jp iburst
server ntp.jst.mfeed.ad.jp iburst
allow 172.20.0.0/16
EOF

systemctl restart chrony
systemctl enable chrony
echo "  -> NTP server running"

# 6. Timezone
echo "[6/7] Setting timezone to Asia/Tokyo..."
timedatectl set-timezone Asia/Tokyo
echo "  -> Timezone set"

# 7. WireGuard VPN
echo "[7/7] Setting up WireGuard VPN..."
apt-get install -y wireguard > /dev/null 2>&1

if [ ! -f /etc/wireguard/wg0.conf ]; then
    SERVER_PRIV=$(wg genkey)
    SERVER_PUB=$(echo "$SERVER_PRIV" | wg pubkey)
    CLIENT_PRIV=$(wg genkey)
    CLIENT_PUB=$(echo "$CLIENT_PRIV" | wg pubkey)

    cat > /etc/wireguard/wg0.conf << EOF
[Interface]
PrivateKey = ${SERVER_PRIV}
Address = 10.100.0.1/24
ListenPort = 51820

[Peer]
PublicKey = ${CLIENT_PUB}
AllowedIPs = 10.100.0.2/32
EOF
    chmod 600 /etc/wireguard/wg0.conf

    echo ""
    echo "  ┌─────────────────────────────────────────┐"
    echo "  │  WireGuard Client Config                 │"
    echo "  ├─────────────────────────────────────────┤"
    echo "  │  [Interface]                             │"
    echo "  │  PrivateKey = ${CLIENT_PRIV}"
    echo "  │  Address = 10.100.0.2/24                 │"
    echo "  │                                          │"
    echo "  │  [Peer]                                  │"
    echo "  │  PublicKey = ${SERVER_PUB}"
    echo "  │  Endpoint = <SERVER_IP>:51820            │"
    echo "  │  AllowedIPs = 10.100.0.0/24,172.20.0.0/16│"
    echo "  │  PersistentKeepalive = 25                │"
    echo "  └─────────────────────────────────────────┘"
    echo ""
    echo "  ** Save this config! It won't be shown again. **"
else
    echo "  -> wg0.conf already exists, skipping keygen"
fi

systemctl enable --now wg-quick@wg0
echo "  -> WireGuard running on :51820/UDP"

echo ""
echo "=== Host network setup complete ==="
echo ""
echo "Next steps:"
echo "  1. cd /opt/millicall"
echo "  2. cp .env.example .env   # edit as needed"
echo "  3. docker compose up -d"
echo "  4. Open http://172.20.0.1 (from phone network)"
echo "     or http://<server-ip> (from LAN)"

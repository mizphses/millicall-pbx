#!/bin/bash
# Host network setup for Millicall PBX
# Run this on the server BEFORE docker compose up
set -e

echo "=== Millicall PBX Host Network Setup ==="

# 1. Configure enp3s0 with static IP
echo "[1/4] Configuring enp3s0 (172.20.0.1/16)..."
cat > /etc/netplan/60-enp3s0.yaml << 'EOF'
network:
  version: 2
  ethernets:
    enp3s0:
      addresses:
        - 172.20.0.1/16
      link-local: []
EOF
netplan apply
echo "  -> enp3s0 configured"

# 2. Enable IP forwarding
echo "[2/4] Enabling IP forwarding..."
cat > /etc/sysctl.d/99-millicall.conf << 'EOF'
net.ipv4.ip_forward=1
EOF
sysctl -p /etc/sysctl.d/99-millicall.conf
echo "  -> IP forwarding enabled"

# 3. NAT rules
echo "[3/4] Setting up NAT (masquerade)..."
apt-get install -y iptables-persistent > /dev/null 2>&1 || true

iptables -t nat -C POSTROUTING -s 172.20.0.0/16 -o wlp2s0 -j MASQUERADE 2>/dev/null || \
    iptables -t nat -A POSTROUTING -s 172.20.0.0/16 -o wlp2s0 -j MASQUERADE

iptables -C FORWARD -i enp3s0 -o wlp2s0 -j ACCEPT 2>/dev/null || \
    iptables -A FORWARD -i enp3s0 -o wlp2s0 -j ACCEPT

iptables -C FORWARD -i wlp2s0 -o enp3s0 -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || \
    iptables -A FORWARD -i wlp2s0 -o enp3s0 -m state --state RELATED,ESTABLISHED -j ACCEPT

netfilter-persistent save
echo "  -> NAT rules configured"

# 4. DHCP server for 172.20 network
echo "[4/4] Setting up DHCP (dnsmasq)..."
apt-get install -y dnsmasq > /dev/null 2>&1

cat > /etc/dnsmasq.d/millicall.conf << 'EOF'
interface=enp3s0
bind-interfaces
dhcp-range=172.20.1.1,172.20.254.254,255.255.0.0,12h
dhcp-option=3,172.20.0.1
dhcp-option=6,172.20.0.1
EOF

systemctl restart dnsmasq
systemctl enable dnsmasq
echo "  -> DHCP server running on enp3s0"

echo ""
echo "=== Host network setup complete ==="
echo "Next: docker compose up -d"

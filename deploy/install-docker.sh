#!/bin/bash
# Install Docker on Ubuntu 24.04
set -e

echo "=== Installing Docker ==="

# Remove old versions
apt-get remove -y docker.io docker-doc docker-compose podman-docker containerd runc 2>/dev/null || true

# Install prerequisites
apt-get update
apt-get install -y ca-certificates curl

# Add Docker GPG key
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

# Add Docker repo
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add current user to docker group
SUDO_USER_NAME="${SUDO_USER:-$USER}"
usermod -aG docker "$SUDO_USER_NAME" 2>/dev/null || true

systemctl enable docker
systemctl start docker

echo "=== Docker installed successfully ==="
docker --version
docker compose version

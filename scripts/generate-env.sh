#!/usr/bin/env bash
# =============================================================================
# Millicall PBX — .env generator
# Generates a .env file with cryptographically strong random secrets.
# =============================================================================
set -euo pipefail

ENV_FILE="${1:-.env}"

if [ -f "$ENV_FILE" ]; then
    echo "⚠  $ENV_FILE already exists."
    read -rp "   Overwrite? [y/N] " answer
    if [[ ! "$answer" =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi
fi

gen_secret() { python3 -c "import secrets; print(secrets.token_urlsafe($1))"; }

JWT_SECRET=$(gen_secret 64)
ADMIN_PASSWORD=$(gen_secret 16)
WEBRTC_PASSWORD=$(gen_secret 16)
ARI_PASSWORD=$(gen_secret 16)

cat > "$ENV_FILE" <<EOF
# =============================================================================
# Millicall PBX — Environment Variables (auto-generated)
# =============================================================================

# --- Database ----------------------------------------------------------------
DATABASE_URL=sqlite+aiosqlite:///./data/millicall.db

# --- Asterisk paths ----------------------------------------------------------
ASTERISK_CONFIG_DIR=/etc/asterisk
ASTERISK_TEMPLATES_DIR=/app/asterisk_templates

# --- Network -----------------------------------------------------------------
PBX_BIND_ADDRESS=0.0.0.0
WEB_HOST=0.0.0.0
WEB_PORT=8000

# --- Security ----------------------------------------------------------------
JWT_SECRET=${JWT_SECRET}
ADMIN_PASSWORD=${ADMIN_PASSWORD}
WEBRTC_PASSWORD=${WEBRTC_PASSWORD}

# --- API security / customization --------------------------------------------
ALLOWED_HOSTS=millicall.local,localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost,http://127.0.0.1
SESSION_COOKIE_NAME=millicall_token
SESSION_COOKIE_SECURE=
SESSION_COOKIE_SAMESITE=lax

# --- Asterisk REST Interface (ARI) -------------------------------------------
ARI_USER=millicall
ARI_PASSWORD=${ARI_PASSWORD}

# --- LLM / AI API Keys (set the ones you use) --------------------------------
GOOGLE_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# --- TTS: CoeFont (optional) -------------------------------------------------
COEFONT_ACCESS_KEY=
COEFONT_ACCESS_SECRET=
COEFONT_VOICE_ID=

# --- Cloudflare Tunnel (optional) --------------------------------------------
CLOUDFLARE_TUNNEL_TOKEN=
EOF

chmod 600 "$ENV_FILE"

echo ""
echo "✅ $ENV_FILE generated successfully!"
echo ""
echo "   Admin password: ${ADMIN_PASSWORD}"
echo ""
echo "   Next steps:"
echo "   1. Set your LLM API keys in $ENV_FILE"
echo "   2. Run: docker compose up -d"
echo ""

#!/usr/bin/env bash
# =============================================================================
#  setup_baxter.sh — Baxter Pipeline One-Command Setup
#  Run on a fresh Ubuntu 22.04/24.04 server.
#
#  USAGE:
#    chmod +x setup_baxter.sh
#    sudo ./setup_baxter.sh
#
#  After completion:
#    Grafana → http://<SERVER_IP>:3000   (admin / admin123)
# =============================================================================

set -euo pipefail

# ── Colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC}  $1"; }
success() { echo -e "${GREEN}[OK]${NC}    $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ── Config ────────────────────────────────────────────────────────────────────
REPO_URL="https://github.com/mjhanzaibmemon/baxter.git"
REPO_BRANCH="main"
INSTALL_DIR="/opt/baxter"

GF_ADMIN_USER="admin"
GF_ADMIN_PASSWORD="admin123"
POSTGRES_PASSWORD="baxter_secret_123"

GRAPH_TENANT_ID="REPLACE_TENANT_ID"
GRAPH_CLIENT_ID="REPLACE_CLIENT_ID"
GRAPH_CLIENT_SECRET="REPLACE_CLIENT_SECRET"
MAILBOX_EMAIL="REPLACE_MAILBOX_EMAIL"
ALLOWED_SENDERS="REPLACE_ALLOWED_SENDERS"

# ── Override above with baxter.env if present alongside this script ───────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/baxter.env" ]]; then
  # shellcheck disable=SC1091
  source "$SCRIPT_DIR/baxter.env"
  echo "[INFO]  Loaded credentials from $SCRIPT_DIR/baxter.env"
fi

# EBS persistent storage path (must be mounted before running this script)
DATA_DIR="/data"

# ─────────────────────────────────────────────────────────────────────────────

[[ $EUID -ne 0 ]] && error "Run as root: sudo ./setup_baxter.sh"

echo ""
echo "============================================================"
echo "   Baxter Pipeline Setup — starting"
echo "============================================================"
echo ""

# ── 0. EBS persistent storage setup ──────────────────────────────────────────
info "Checking EBS persistent storage at $DATA_DIR..."

# Find unformatted EBS volume (not the root disk nvme0n1)
EBS_DEV=""
for dev in /dev/nvme1n1 /dev/xvdbb /dev/xvdb /dev/sdb; do
  if [[ -b "$dev" ]]; then
    EBS_DEV="$dev"
    break
  fi
done

if [[ -z "$EBS_DEV" ]]; then
  warn "No secondary EBS volume found — data will be stored on root disk (not recommended for production)"
else
  # Format only if not already formatted
  FS_TYPE=$(blkid -s TYPE -o value "$EBS_DEV" 2>/dev/null || echo "")
  if [[ -z "$FS_TYPE" ]]; then
    info "Formatting $EBS_DEV as ext4..."
    mkfs.ext4 -L baxter-data "$EBS_DEV"
    success "$EBS_DEV formatted"
  else
    info "$EBS_DEV already formatted ($FS_TYPE) — skipping format"
  fi

  # Mount if not already mounted
  if ! mountpoint -q "$DATA_DIR"; then
    mkdir -p "$DATA_DIR"
    mount "$EBS_DEV" "$DATA_DIR"
    success "$EBS_DEV mounted at $DATA_DIR"
  else
    info "$DATA_DIR already mounted"
  fi

  # Add to fstab if not already there
  if ! grep -q "$DATA_DIR" /etc/fstab; then
    EBS_UUID=$(blkid -s UUID -o value "$EBS_DEV")
    echo "UUID=$EBS_UUID  $DATA_DIR  ext4  defaults,nofail  0  2" >> /etc/fstab
    success "Added $DATA_DIR to /etc/fstab (persists on reboot)"
  fi
fi

# Create data subdirectories for postgres and grafana
mkdir -p "$DATA_DIR/postgres" "$DATA_DIR/grafana"
chown -R 999:999 "$DATA_DIR/postgres"
chown -R 472:472 "$DATA_DIR/grafana"
success "Data directories ready: $DATA_DIR/postgres  $DATA_DIR/grafana"

# ── 1. System update ─────────────────────────────────────────────────────────
info "Updating system packages..."
apt-get update -qq
apt-get upgrade -y -qq
success "System updated"

# ── 2. Base packages ──────────────────────────────────────────────────────────
info "Installing git, curl, ca-certificates..."
apt-get install -y -qq git curl ca-certificates gnupg lsb-release
success "Base packages installed"

# ── 3. Docker (official repo) ─────────────────────────────────────────────────
if command -v docker &>/dev/null; then
  warn "Docker already installed: $(docker --version)"
else
  info "Installing Docker..."
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg

  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu \
    $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    > /etc/apt/sources.list.d/docker.list

  apt-get update -qq
  apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable docker
  systemctl start docker
  success "Docker installed: $(docker --version)"
fi

docker compose version &>/dev/null || error "Docker Compose plugin not found"
success "Docker Compose: $(docker compose version)"

# ── 4. Clone project ──────────────────────────────────────────────────────────
if [[ -d "$INSTALL_DIR/.git" ]]; then
  info "Repo exists — pulling latest..."
  cd "$INSTALL_DIR"
  git fetch origin
  git reset --hard "origin/$REPO_BRANCH"
  success "Repo updated"
else
  info "Cloning repo to $INSTALL_DIR..."
  git clone --branch "$REPO_BRANCH" "$REPO_URL" "$INSTALL_DIR"
  success "Repo cloned"
fi

cd "$INSTALL_DIR"

# ── 5. Write .env ─────────────────────────────────────────────────────────────
info "Writing .env file..."
cat > "$INSTALL_DIR/.env" <<EOF
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
GF_SECURITY_ADMIN_USER=${GF_ADMIN_USER}
GF_SECURITY_ADMIN_PASSWORD=${GF_ADMIN_PASSWORD}
GRAPH_TENANT_ID=${GRAPH_TENANT_ID}
GRAPH_CLIENT_ID=${GRAPH_CLIENT_ID}
GRAPH_CLIENT_SECRET=${GRAPH_CLIENT_SECRET}
MAILBOX_EMAIL=${MAILBOX_EMAIL}
ALLOWED_SENDERS=${ALLOWED_SENDERS}
DEMO_MODE=false
POLL_INTERVAL_MINUTES=1
ALLOWED_FILE_KEYWORDS=MS_Kargo,CS_RMA,Result_,order_level
EOF
success ".env written"

# ── 6. Start containers ───────────────────────────────────────────────────────
info "Building and starting containers (this takes a few minutes)..."
docker compose up -d --build
success "Containers started"

# ── 7. Health checks ──────────────────────────────────────────────────────────
info "Waiting for services to become healthy..."
MAX_WAIT=120
ELAPSED=0
while true; do
  PG=$(docker inspect --format='{{.State.Health.Status}}' baxter_postgres 2>/dev/null || echo "missing")
  ING=$(docker inspect --format='{{.State.Health.Status}}' baxter_ingestor 2>/dev/null || echo "missing")

  if [[ "$PG" == "healthy" && "$ING" == "healthy" ]]; then
    success "PostgreSQL: healthy"
    success "Ingestor:   healthy"
    break
  fi

  if (( ELAPSED >= MAX_WAIT )); then
    warn "Timeout after ${MAX_WAIT}s — check: docker ps"
    break
  fi

  echo -n "."
  sleep 5
  (( ELAPSED += 5 ))
done
echo ""

GF_RUNNING=$(docker inspect --format='{{.State.Running}}' baxter_grafana 2>/dev/null || echo "false")
[[ "$GF_RUNNING" == "true" ]] && success "Grafana:    running" \
  || warn "Grafana not running — check: docker logs baxter_grafana"

# ── Done ──────────────────────────────────────────────────────────────────────
SERVER_IP=$(hostname -I | awk '{print $1}')
echo ""
echo "============================================================"
echo -e "  ${GREEN}Baxter Pipeline is up and running!${NC}"
echo "============================================================"
echo ""
echo "  Grafana:  http://${SERVER_IP}:3000"
echo "  Username: ${GF_ADMIN_USER}   Password: ${GF_ADMIN_PASSWORD}"
echo ""
echo "  Container status:"
docker ps --format "    {{.Names}}\t{{.Status}}"
echo ""
echo "  Useful commands:"
echo "    docker logs baxter_ingestor -f"
echo "    docker compose -f $INSTALL_DIR/docker-compose.yml restart"
echo ""
echo "  NOTE: Port 3000 must be open in your firewall/security group."
echo "============================================================"

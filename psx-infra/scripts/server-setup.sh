#!/usr/bin/env bash
# PSX App — Initial Hetzner Server Setup
# Run as root on a fresh Ubuntu 22.04 LTS server.
# Usage: bash server-setup.sh <app_user> <your_ssh_public_key>
# Example: bash server-setup.sh psx "ssh-ed25519 AAAAC3... you@machine"
#
# What this script does:
#   1. System update
#   2. Creates a non-root application user (no sudo)
#   3. Installs Docker + Docker Compose plugin
#   4. Configures ufw firewall (22, 80, 443 only)
#   5. Hardens SSH (key-only, no root login, no password auth)
#   6. Installs and configures fail2ban
#   7. Enables unattended-upgrades for security patches

set -euo pipefail

APP_USER="${1:?Usage: $0 <app_user> <ssh_public_key>}"
SSH_PUBLIC_KEY="${2:?Usage: $0 <app_user> <ssh_public_key>}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

# ─── 1. System update ─────────────────────────────────────────────────────────
log "Updating system packages..."
apt-get update -qq
apt-get upgrade -y -qq
apt-get install -y -qq \
    curl wget git unzip ca-certificates gnupg lsb-release \
    fail2ban ufw htop jq

# ─── 2. Create application user ───────────────────────────────────────────────
log "Creating application user: ${APP_USER}..."
if ! id "${APP_USER}" &>/dev/null; then
    useradd --create-home --shell /bin/bash "${APP_USER}"
fi

# Give app user access to Docker (added to docker group after Docker install)
mkdir -p "/home/${APP_USER}/.ssh"
echo "${SSH_PUBLIC_KEY}" > "/home/${APP_USER}/.ssh/authorized_keys"
chmod 700 "/home/${APP_USER}/.ssh"
chmod 600 "/home/${APP_USER}/.ssh/authorized_keys"
chown -R "${APP_USER}:${APP_USER}" "/home/${APP_USER}/.ssh"
log "App user created. SSH key installed."

# ─── 3. Install Docker ────────────────────────────────────────────────────────
log "Installing Docker..."
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
    > /etc/apt/sources.list.d/docker.list

apt-get update -qq
apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

systemctl enable docker
systemctl start docker

# Add app user to docker group (no need for sudo to run docker)
usermod -aG docker "${APP_USER}"
log "Docker installed. Version: $(docker --version)"

# ─── 4. Firewall ──────────────────────────────────────────────────────────────
log "Configuring ufw firewall..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    comment "SSH"
ufw allow 80/tcp    comment "HTTP"
ufw allow 443/tcp   comment "HTTPS"
# Internal Docker network — allow containers to talk to each other
ufw allow from 172.16.0.0/12 comment "Docker internal networks"
ufw --force enable
log "Firewall active. Rules:"
ufw status numbered

# ─── 5. Harden SSH ────────────────────────────────────────────────────────────
log "Hardening SSH configuration..."
SSHD_CONFIG="/etc/ssh/sshd_config"

# Back up the original
cp "${SSHD_CONFIG}" "${SSHD_CONFIG}.bak.$(date +%Y%m%d)"

cat > /etc/ssh/sshd_config.d/99-hardening.conf <<'EOF'
# PSX App SSH Hardening
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
AuthorizedKeysFile .ssh/authorized_keys
PermitEmptyPasswords no
X11Forwarding no
AllowTcpForwarding no
MaxAuthTries 3
LoginGraceTime 30
ClientAliveInterval 300
ClientAliveCountMax 2
# Only allow the app user (add more users with space-separated list if needed)
EOF

# Validate config before reloading
sshd -t && systemctl reload ssh
log "SSH hardened. Password auth disabled, root login disabled."

# ─── 6. fail2ban ──────────────────────────────────────────────────────────────
log "Configuring fail2ban..."
cat > /etc/fail2ban/jail.local <<'EOF'
[DEFAULT]
bantime  = 3600
findtime = 600
maxretry = 5
backend  = systemd

[sshd]
enabled  = true
port     = ssh
maxretry = 3
bantime  = 86400
EOF

systemctl enable fail2ban
systemctl restart fail2ban
log "fail2ban active. SSH: 3 attempts max, 24h ban."

# ─── 7. Unattended security upgrades ──────────────────────────────────────────
log "Enabling unattended-upgrades..."
apt-get install -y -qq unattended-upgrades
cat > /etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF
systemctl enable unattended-upgrades
log "Unattended security upgrades enabled."

# ─── 8. Application directory ─────────────────────────────────────────────────
log "Creating application directory..."
mkdir -p /opt/psx-app
chown "${APP_USER}:${APP_USER}" /opt/psx-app
log "App directory: /opt/psx-app (owned by ${APP_USER})"

# ─── Done ─────────────────────────────────────────────────────────────────────
log "======================================"
log "Server setup complete."
log "  App user : ${APP_USER}"
log "  App dir  : /opt/psx-app"
log "  Docker   : $(docker --version)"
log "  Firewall : ufw active (22, 80, 443)"
log "  SSH      : key-only, root login disabled"
log "  fail2ban : active"
log ""
log "NEXT STEPS:"
log "  1. Log out of root and verify SSH login as ${APP_USER} works"
log "  2. Clone the repo to /opt/psx-app as ${APP_USER}"
log "  3. Run: cd /opt/psx-app/psx-infra && docker compose -f docker-compose.staging.yml up -d"
log "======================================"

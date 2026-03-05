# EC2 + EBS Setup Guide for Baxter Pipeline

## Step 1: Create EBS Volume (AWS Console)

1. **Go to EC2 Dashboard** → **Elastic Block Store** → **Volumes**
2. Click **Create Volume**
3. Settings:
   - **Volume Type:** gp3 (recommended) or gp2
   - **Size:** 20-50 GB (adjust based on data needs)
   - **Availability Zone:** ⚠️ MUST match your EC2 instance's AZ (e.g., `us-east-1a`)
   - **Encryption:** Enable (recommended)
4. Click **Create Volume**
5. Note the **Volume ID** (e.g., `vol-0abc123def456`)

---

## Step 2: Attach EBS to EC2 (AWS Console)

1. Select the volume → **Actions** → **Attach Volume**
2. Select your EC2 instance
3. Device name: `/dev/xvdf` (or `/dev/sdf`)
4. Click **Attach**

---

## Step 3: EC2 User Data Script

Copy this script and paste it in **EC2 Launch → Advanced Details → User Data** when launching a new instance:

```bash
#!/bin/bash
set -e

# ============================================
# BAXTER PIPELINE - EC2 USER DATA SCRIPT
# ============================================
# This script:
# 1. Formats and mounts EBS volume
# 2. Installs Docker & Docker Compose
# 3. Clones and runs the Baxter pipeline
# 4. Sets up auto-mount on reboot
# ============================================

LOG_FILE="/var/log/baxter-setup.log"
exec > >(tee -a $LOG_FILE) 2>&1
echo "=== Baxter Setup Started: $(date) ==="

# -----------------
# CONFIGURATION
# -----------------
EBS_DEVICE="/dev/xvdf"           # Change if using different device
MOUNT_POINT="/data"              # Where EBS will be mounted
REPO_URL="https://github.com/mjhanzaibmemon/baxter.git"
BRANCH="main"                    # or "beta"

# -----------------
# 1. WAIT FOR EBS VOLUME
# -----------------
echo "Waiting for EBS volume to be available..."
while [ ! -e "$EBS_DEVICE" ]; do
    sleep 5
    echo "Waiting for $EBS_DEVICE..."
done
echo "EBS device found: $EBS_DEVICE"

# -----------------
# 2. FORMAT EBS (only if not already formatted)
# -----------------
if ! blkid "$EBS_DEVICE" | grep -q "ext4"; then
    echo "Formatting EBS volume as ext4..."
    mkfs -t ext4 "$EBS_DEVICE"
else
    echo "EBS already formatted, skipping format."
fi

# -----------------
# 3. MOUNT EBS
# -----------------
mkdir -p "$MOUNT_POINT"
mount "$EBS_DEVICE" "$MOUNT_POINT"
echo "EBS mounted at $MOUNT_POINT"

# -----------------
# 4. ADD TO FSTAB (auto-mount on reboot)
# -----------------
EBS_UUID=$(blkid -s UUID -o value "$EBS_DEVICE")
if ! grep -q "$EBS_UUID" /etc/fstab; then
    echo "UUID=$EBS_UUID $MOUNT_POINT ext4 defaults,nofail 0 2" >> /etc/fstab
    echo "Added EBS to /etc/fstab for persistence"
fi

# -----------------
# 5. INSTALL DOCKER
# -----------------
echo "Installing Docker..."
yum update -y
yum install -y docker git
systemctl start docker
systemctl enable docker
usermod -aG docker ec2-user

# -----------------
# 6. INSTALL DOCKER COMPOSE
# -----------------
echo "Installing Docker Compose..."
DOCKER_COMPOSE_VERSION="v2.24.0"
curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose

# -----------------
# 7. CREATE APP DIRECTORIES ON EBS
# -----------------
APP_DIR="$MOUNT_POINT/baxter"
POSTGRES_DATA="$MOUNT_POINT/postgres_data"
GRAFANA_DATA="$MOUNT_POINT/grafana_data"

mkdir -p "$APP_DIR" "$POSTGRES_DATA" "$GRAFANA_DATA"
chown -R 1000:1000 "$GRAFANA_DATA"  # Grafana runs as UID 1000

# -----------------
# 8. CLONE REPOSITORY
# -----------------
echo "Cloning Baxter repository..."
if [ -d "$APP_DIR/.git" ]; then
    cd "$APP_DIR"
    git pull origin "$BRANCH"
else
    git clone -b "$BRANCH" "$REPO_URL" "$APP_DIR"
fi

# -----------------
# 9. CREATE .env FILE
# -----------------
cat > "$APP_DIR/.env" << 'ENVFILE'
# === MICROSOFT GRAPH API ===
TENANT_ID=your-tenant-id
CLIENT_ID=your-client-id
CLIENT_SECRET=your-client-secret
MAILBOX_EMAIL=your-mailbox@domain.com

# === ALERT SETTINGS ===
ALERT_EMAIL=your-alert-email@domain.com

# === FILTERS ===
ALLOWED_SENDERS=sender1@domain.com,sender2@domain.com
ALLOWED_FILE_KEYWORDS=MS_Kargo,CS_RMA

# === POLLING ===
POLL_INTERVAL_MINUTES=5

# === DATABASE ===
POSTGRES_DB=baxter_demo
POSTGRES_USER=baxter
POSTGRES_PASSWORD=secure_password_change_me
ENVFILE

echo "⚠️  IMPORTANT: Edit $APP_DIR/.env with your actual credentials!"

# -----------------
# 10. UPDATE DOCKER-COMPOSE FOR EBS VOLUMES
# -----------------
# Create override file to use EBS for persistent data
cat > "$APP_DIR/docker-compose.override.yml" << OVERRIDE
version: '3.8'
services:
  postgres:
    volumes:
      - $POSTGRES_DATA:/var/lib/postgresql/data
  grafana:
    volumes:
      - $GRAFANA_DATA:/var/lib/grafana
OVERRIDE

# -----------------
# 11. START SERVICES
# -----------------
cd "$APP_DIR"
docker-compose pull
docker-compose up -d

# -----------------
# 12. CREATE SYSTEMD SERVICE (auto-start on boot)
# -----------------
cat > /etc/systemd/system/baxter.service << SERVICE
[Unit]
Description=Baxter Pipeline
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$APP_DIR
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
User=root

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable baxter.service

echo "=== Baxter Setup Complete: $(date) ==="
echo "Services running. Access Grafana at http://<EC2-PUBLIC-IP>:3000"
```

---

## Step 4: For EXISTING EC2 (Manual Setup)

If you already have an EC2 instance running, SSH into it and run this script:

```bash
#!/bin/bash
# MANUAL EBS SETUP SCRIPT
# Run as root: sudo bash setup_ebs.sh

EBS_DEVICE="/dev/xvdf"
MOUNT_POINT="/data"

# Check if device exists
if [ ! -e "$EBS_DEVICE" ]; then
    echo "ERROR: $EBS_DEVICE not found. Attach EBS first!"
    exit 1
fi

# Format if needed
if ! blkid "$EBS_DEVICE" | grep -q "ext4"; then
    echo "Formatting EBS..."
    mkfs -t ext4 "$EBS_DEVICE"
fi

# Mount
mkdir -p "$MOUNT_POINT"
mount "$EBS_DEVICE" "$MOUNT_POINT"

# Add to fstab
EBS_UUID=$(blkid -s UUID -o value "$EBS_DEVICE")
if ! grep -q "$EBS_UUID" /etc/fstab; then
    echo "UUID=$EBS_UUID $MOUNT_POINT ext4 defaults,nofail 0 2" >> /etc/fstab
fi

echo "EBS mounted at $MOUNT_POINT"
df -h "$MOUNT_POINT"
```

---

## Step 5: AWS CLI Commands (Alternative)

If you prefer CLI over Console:

```bash
# Create EBS Volume
aws ec2 create-volume \
    --availability-zone us-east-1a \
    --size 30 \
    --volume-type gp3 \
    --tag-specifications 'ResourceType=volume,Tags=[{Key=Name,Value=baxter-data}]'

# Attach to EC2 (replace IDs)
aws ec2 attach-volume \
    --volume-id vol-0abc123def456 \
    --instance-id i-0abc123def456 \
    --device /dev/xvdf
```

---

## Important Notes

| Item | Details |
|------|---------|
| **EBS AZ** | Must match EC2 instance's Availability Zone |
| **Device Name** | Usually `/dev/xvdf` or `/dev/sdf` (shows as `/dev/nvme1n1` on Nitro instances) |
| **Persist on Stop** | EBS data survives EC2 stop/start |
| **Persist on Terminate** | Enable "Delete on Termination = No" for EBS |
| **Backup** | Create EBS Snapshots regularly |

---

## Nitro Instances (t3, m5, c5, etc.)

On Nitro-based instances, device names are different:

```bash
# Check actual device name
lsblk

# Usually shows as:
# /dev/nvme0n1 - root volume
# /dev/nvme1n1 - your EBS volume

# Update script to use:
EBS_DEVICE="/dev/nvme1n1"
```

---

## Security Group Requirements

Ensure your EC2 Security Group allows:

| Port | Protocol | Source | Purpose |
|------|----------|--------|---------|
| 22 | TCP | Your IP | SSH access |
| 3000 | TCP | Your IP | Grafana dashboard |
| 5432 | TCP | 127.0.0.1 only | PostgreSQL (internal) |

---

## Quick Checklist

- [ ] Create EBS in same AZ as EC2
- [ ] Attach EBS to EC2
- [ ] Launch EC2 with User Data script (or run manual script)
- [ ] Edit `.env` file with your Graph API credentials
- [ ] Open Security Group ports (22, 3000)
- [ ] Access Grafana at `http://<EC2-IP>:3000`

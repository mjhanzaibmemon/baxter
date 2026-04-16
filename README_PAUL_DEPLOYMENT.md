# Baxter Analytics Pipeline — Deployment Runbook for Paul's IT Team

**Complete one-command setup for fresh Ubuntu EC2 server with Docker, PostgreSQL, Grafana, and auto-ingest.**

---

## Prerequisites (Before Running Setup)

### 1. **AWS EC2 Instance** (Fresh Ubuntu 24.04 or 22.04)
- **Instance Type:** t3.micro or t3.small minimum
- **Root Volume:** 20 GB (gp3 recommended)
- **Same Availability Zone** as your organization's resources

### 2. **EBS Persistent Storage** (10 GB recommended)
- Attach new EBS volume to instance (same AZ)
- **Do NOT format it** — script will auto-detect and format as ext4
- Mounts at `/data` with bind-mount for postgres and grafana

### 3. **Microsoft Graph API Credentials** (For email ingestion)

You MUST complete the **Azure AD Setup** FIRST. See [AZURE_SETUP_GUIDE.html](./docs/AZURE_SETUP_GUIDE.html) for detailed steps.

**Credentials needed:**
- `GRAPH_TENANT_ID` — Microsoft Entra Directory ID
- `GRAPH_CLIENT_ID` — App Registration Client ID  
- `GRAPH_CLIENT_SECRET` — Client Secret (saved safely)
- `MAILBOX_EMAIL` — Email address that receives Excel attachments
- `ALLOWED_SENDERS` — Comma-separated list of approved sender emails

---

## Setup Workflow (4 Steps)

### **Step 1: Download & Prepare Files Locally**

On your **local machine** (Windows/Mac/Linux):

```powershell
# Download the deployment package
# Go to: https://github.com/mjhanzaibmemon/baxter/releases
# Or clone: git clone https://github.com/mjhanzaibmemon/baxter.git
# Extract to a folder: C:\Users\YourName\Desktop\baxter-deploy\

cd C:\Users\YourName\Desktop\baxter-deploy\
```

**Files you'll have:**
- `setup_baxter.sh` — Automated deployment script
- `baxter.env` — Credentials file (to be filled in)
- `README_PAUL_DEPLOYMENT.md` — This file

---

### **Step 2: Fill in Credentials in `baxter.env`**

Open `baxter.env` in a text editor and replace ALL placeholder values:

```bash
# Grafana admin (default, safe to keep)
GF_ADMIN_USER="admin"
GF_ADMIN_PASSWORD="admin123"

# PostgreSQL database password (default, safe to keep)
POSTGRES_PASSWORD="baxter_secret_123"

# ⚠️ REQUIRED: Fill in your Microsoft Graph API credentials
GRAPH_TENANT_ID="[PASTE_YOUR_TENANT_ID_HERE]"
GRAPH_CLIENT_ID="[PASTE_YOUR_CLIENT_ID_HERE]"
GRAPH_CLIENT_SECRET="[PASTE_YOUR_CLIENT_SECRET_HERE]"
MAILBOX_EMAIL="[PASTE_YOUR_MAILBOX_EMAIL]"
ALLOWED_SENDERS="[PASTE_APPROVED_SENDERS,COMMA,SEPARATED]"
```

**Example (filled in - do NOT use these, use YOUR own credentials):**
```bash
GRAPH_TENANT_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
GRAPH_CLIENT_ID="yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy"
GRAPH_CLIENT_SECRET="[YOUR_ACTUAL_SECRET_FROM_AZURE]"
MAILBOX_EMAIL="logistics@yourcompany.com"
ALLOWED_SENDERS="logistics@yourcompany.com,paul.delfava@baxter.com"
```

**⚠️ SECURITY:** Keep this file safe. Never commit to Git. This file contains secrets.

---

### **Step 3: Copy Files to EC2 Instance**

**Option A: Using SSH (Recommended)**

On your local machine, run:

#### **Windows PowerShell:**
```powershell
# Variables
$INSTANCE_IP = "ec2-18-221-90-188.us-east-2.compute.amazonaws.com"  # Replace with YOUR instance IP
$SSH_KEY = "$env:USERPROFILE\Downloads\rdp.pem"                    # Path to your SSH key
$LOCAL_DIR = "C:\Users\YourName\Desktop\baxter-deploy"             # Your local folder

# Copy files to home directory
scp -i $SSH_KEY -o StrictHostKeyChecking=no `
  "$LOCAL_DIR\setup_baxter.sh" `
  "$LOCAL_DIR\baxter.env" `
  ubuntu@${INSTANCE_IP}:/home/ubuntu/

# Verify upload
ssh -i $SSH_KEY ubuntu@${INSTANCE_IP} "ls -lah ~/setup_baxter.sh ~/baxter.env"
```

#### **Mac/Linux Terminal:**
```bash
INSTANCE_IP="ec2-18-221-90-188.us-east-2.compute.amazonaws.com"  # Replace
SSH_KEY="$HOME/.ssh/rdp.pem"
LOCAL_DIR="$HOME/Desktop/baxter-deploy"

scp -i $SSH_KEY -o StrictHostKeyChecking=no \
  $LOCAL_DIR/setup_baxter.sh \
  $LOCAL_DIR/baxter.env \
  ubuntu@${INSTANCE_IP}:/home/ubuntu/

ssh -i $SSH_KEY ubuntu@${INSTANCE_IP} "ls -lah ~/setup_baxter.sh ~/baxter.env"
```

**Option B: Using RDP + Manual Copy**

If SSH is not available:
1. RDP into instance
2. Copy files via file manager to home directory

---

### **Step 4: Run the Setup Script**

**SSH into EC2 instance:**

```bash
ssh -i /path/to/rdp.pem ubuntu@<YOUR_INSTANCE_IP>
```

**Run the setup script:**

```bash
cd ~
chmod +x setup_baxter.sh
sudo ./setup_baxter.sh 2>&1 | tee setup.log
```

**Script will:**
1. ✅ Auto-detect & format EBS volume (if present)
2. ✅ Install Docker, Docker Compose
3. ✅ Clone GitHub repo to `/opt/baxter`
4. ✅ Source credentials from `baxter.env`
5. ✅ Start 3 Docker containers: postgres, grafana, ingestor
6. ✅ Wait 120 seconds for health checks
7. ✅ Auto-ingest ALL data files from `sample_data/` directory
8. ✅ Print success message with Grafana URL

**Expected output (end of log):**
```
[OK]    All services healthy ✅
[OK]    Auto-ingest completed: 21 files processed
[OK]    Setup complete! Grafana ready at http://<INSTANCE_IP>:3000
[OK]    Login: admin / admin123
```

---

## After Setup: Verify Everything Works

### **1. Check Grafana Dashboard**

```
URL: http://<YOUR_INSTANCE_IP>:3000
Login: admin / admin123
```

**Dashboards should show:**
- ✅ Order & Claims Summary (main dashboard)
- ✅ Volume over time
- ✅ Shipment breakdown
- ✅ Claim validation details
- ✅ V2 summary (VP dashboard)

**Metrics should populate:**
- Orders Shipped: 6,077+
- Claims Submitted: 1,859+
- Verified Shortages: 63+
- $ Saved: $123,904.87+

### **2. Check Container Health**

```bash
ssh -i /path/to/rdp.pem ubuntu@<YOUR_INSTANCE_IP>

# Check running containers
docker ps

# Expected output:
# CONTAINER ID   IMAGE                    STATUS
# abc123...      postgres:15-alpine       Up X minutes (healthy)
# def456...      grafana/grafana:11.3.0   Up X minutes (healthy)
# ghi789...      baxter-ingestor:latest   Up X minutes (healthy)
```

### **3. Check Database**

```bash
sudo docker exec baxter_postgres psql -U baxter -d baxter_demo -c \
  "SELECT relname, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC;"

# Expected output:
# shipments        | 97830
# claim_details    | 15456
# rma_credits      | 267
```

---

## Ongoing Operations

### **Adding New Data**

After initial setup, new data files can be added via:

1. **Email (Automatic):** Send Excel/CSV to configured mailbox → Ingestor processes automatically
2. **Manual Upload:** SSH into instance and run:
   ```bash
   sudo docker exec baxter_ingestor python manual_upload.py /app/sample_data/FILENAME.csv
   ```

### **Restarting Services**

```bash
# Restart individual service
sudo docker compose -f /opt/baxter/docker-compose.yml restart grafana

# Restart all services
sudo docker compose -f /opt/baxter/docker-compose.yml restart

# Stop all (data persists on EBS)
sudo docker compose -f /opt/baxter/docker-compose.yml down
```

### **Viewing Logs**

```bash
# Ingestor logs
sudo docker compose -f /opt/baxter/docker-compose.yml logs -f ingestor

# Grafana logs
sudo docker compose -f /opt/baxter/docker-compose.yml logs -f grafana

# PostgreSQL logs
sudo docker compose -f /opt/baxter/docker-compose.yml logs -f postgres
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Script fails with "docker command not found" | Docker install failed — check internet connection, re-run script |
| EBS volume not detected | Manually attach 10GB EBS volume to instance in AWS console (same AZ) |
| Grafana shows "Database error" | Wait 30s, refresh page. Check postgres container: `docker logs baxter_postgres` |
| Ingestor not picking up emails | Verify Graph API credentials in `baxter.env`. Check Graph permissions in Azure AD (must have admin consent ✅) |
| Setup script timeout (120s) | Services booting slow. SSH into instance: `docker ps` to check. Wait 2 mins, refresh Grafana |

---

## Security Notes

- ⚠️ **Keep `baxter.env` secure** — Contains Graph API secrets. Never commit to Git.
- ✅ **EBS volume** — Data persists between restarts (encrypted at rest recommended)
- ✅ **Database** — PostgreSQL inside container, only accessible via Docker network
- ✅ **Grafana** — Default credentials; change in production via `docker exec baxter_grafana grafana-cli admin change-password`
- ✅ **Graph API** — Secrets rotated via Azure AD (recommend 6-month rotation)

---

## Files in This Package

| File | Purpose |
|------|---------|
| `setup_baxter.sh` | Main deployment script (chmod +x, run with sudo) |
| `baxter.env` | Credentials file (fill in before running script) |
| `README_PAUL_DEPLOYMENT.md` | This runbook |
| `docker-compose.yml` | Service definitions (auto-pulled from GitHub) |
| `sample_data/` | Historical data files (auto-ingested on first setup) |

---

## Contact & Support

If you encounter issues:

1. **Check setup.log:** `cat setup.log` (saved in home directory)
2. **Review troubleshooting section above**
3. **Docker health check:** `docker ps` should show all 3 services "Up" and "(healthy)"
4. **Contact Jahanzeb** with setup.log output and specific error message

---

## Quick Reference

**One-liner after prerequisites met:**
```bash
cd ~
chmod +x setup_baxter.sh
sudo ./setup_baxter.sh
```

**Then visit:** `http://<YOUR_INSTANCE_IP>:3000`

**Login:** `admin` / `admin123`

---

**Last Updated:** April 16, 2026  
**Setup Time:** ~5–10 minutes  
**Tested on:** Ubuntu 24.04, 22.04

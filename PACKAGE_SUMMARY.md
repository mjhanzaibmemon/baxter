# BAXTER DEPLOYMENT PACKAGE FOR PAUL'S IT TEAM

**3 Files Ready to Deploy — Follow Instructions Below**

---

## 📦 Package Contents

| File | Purpose | Instructions |
|------|---------|--------------|
| **setup_baxter.sh** | Automated deployment script | Make executable, run with `sudo ./setup_baxter.sh` |
| **baxter.env** | Credentials & configuration | Fill in all [PLACEHOLDER] values BEFORE uploading to EC2 |
| **README_PAUL_DEPLOYMENT.md** | Complete workflow guide | Read first, follow step-by-step |

---

## ⚡ Quick Start (5 Steps)

### **1. Get Credentials Ready**
Before anything else, complete **Azure AD Setup** (see docs/AZURE_SETUP_GUIDE.html):
- Get `GRAPH_TENANT_ID`, `GRAPH_CLIENT_ID`, `GRAPH_CLIENT_SECRET`
- Determine your `MAILBOX_EMAIL` and approved `ALLOWED_SENDERS`

### **2. Fill in baxter.env**
Open `baxter.env` and replace ALL [PLACEHOLDER] values with your credentials:
```bash
GRAPH_TENANT_ID="[YOUR_TENANT_ID_HERE]"
GRAPH_CLIENT_ID="[YOUR_CLIENT_ID_HERE]"
GRAPH_CLIENT_SECRET="[YOUR_CLIENT_SECRET_HERE]"
MAILBOX_EMAIL="[YOUR_MAILBOX_EMAIL]"
ALLOWED_SENDERS="[EMAIL1,EMAIL2,EMAIL3]"
```

### **3. Provision EC2 Instance**
- Launch **Ubuntu 24.04 or 22.04** on AWS (t3.micro minimum)
- **Attach 10GB EBS volume** (gp3, same Availability Zone)
- Enable SSH access (security group)

### **4. Copy Files to Instance**
Run on your local machine (Windows PowerShell / Mac/Linux Terminal):

**Windows PowerShell:**
```powershell
$INSTANCE="ec2-xxx-xxx-xxx.us-east-2.compute.amazonaws.com"  # Your instance
$KEY="C:\Users\YourName\Downloads\rdp.pem"  # Your SSH key
$LOCAL="C:\Users\YourName\Desktop\baxter-deploy"  # Your folder

scp -i $KEY -o StrictHostKeyChecking=no `
  $LOCAL\setup_baxter.sh `
  $LOCAL\baxter.env `
  ubuntu@${INSTANCE}:/home/ubuntu/
```

**Mac/Linux Terminal:**
```bash
INSTANCE="ec2-xxx-xxx-xxx.us-east-2.compute.amazonaws.com"
KEY="$HOME/.ssh/rdp.pem"
LOCAL="$HOME/Desktop/baxter-deploy"

scp -i $KEY -o StrictHostKeyChecking=no \
  $LOCAL/setup_baxter.sh \
  $LOCAL/baxter.env \
  ubuntu@${INSTANCE}:/home/ubuntu/
```

### **5. Run Setup Script**
SSH into instance and execute:
```bash
ssh -i /path/to/rdp.pem ubuntu@<YOUR_INSTANCE_IP>

# Inside instance:
cd ~
chmod +x setup_baxter.sh
sudo ./setup_baxter.sh 2>&1 | tee setup.log
```

**Script will:**
- ✅ Auto-detect & format EBS volume
- ✅ Install Docker & Docker Compose
- ✅ Clone GitHub repository
- ✅ Source credentials from baxter.env
- ✅ Start 3 containers (postgres, grafana, ingestor)
- ✅ Auto-ingest all sample data (97,830+ shipments + 15,456+ claims)
- ✅ Output Grafana URL when done

**Expected time:** 5–10 minutes

---

## 📊 After Setup: Access Grafana

Navigate to: `http://<YOUR_INSTANCE_IP>:3000`

**Login:** `admin` / `admin123`

**Dashboards:**
- 📈 Order & Claims Summary (main KPIs)
- 📉 Volume Over Time
- 📦 Shipment Breakdown
- 🔍 Claim Validation Details
- 🎯 V2 Summary (VP Dashboard)

**Verify metrics:**
- Orders Shipped: 6,077+
- Claims Submitted: 1,859+
- Verified Shortages: 63+
- $ Saved: $123,904.87+

---

## 🔐 Important Notes

- **Security:** Keep `baxter.env` file **confidential** — contains API secrets
- **Persistence:** EBS volume mounts at `/data` — database survives instance reboot
- **Ongoing:** New data files auto-process via email ingestion (configured in `baxter.env`)
- **Backup:** `baxter.env` should be stored safely for future deployments

---

## ❓ Troubleshooting

| Problem | Solution |
|---------|----------|
| Script fails with "docker: command not found" | Docker install failed — check internet, re-run script |
| EBS not detected | Manually attach 10GB volume in AWS console (same AZ as instance) |
| Grafana shows "Database error" | Wait 30s, refresh. Or check: `docker logs baxter_postgres` |
| Graph API errors in ingestor logs | Verify Graph credentials in `baxter.env` — must have admin consent ✅ in Azure AD |
| Setup timeout (>120s) | Services booting slow — wait 2 min, check `docker ps`, refresh Grafana |

**For support:** SSH into instance, check `setup.log` or run `docker compose logs -f`

---

## 📝 Files Summary

```
baxter-deploy/
├── setup_baxter.sh              ← Main script (chmod +x, run with sudo)
├── baxter.env                   ← Fill in credentials (NEVER commit to Git)
├── README_PAUL_DEPLOYMENT.md    ← Full workflow guide (this detailed runbook)
└── PACKAGE_SUMMARY.md           ← Quick reference (this file)
```

---

## ✅ Deployment Checklist

- [ ] Azure AD setup complete (credentials obtained)
- [ ] `baxter.env` filled in with all values (all [PLACEHOLDER]s replaced)
- [ ] EC2 instance launched (Ubuntu 24.04/22.04, t3.micro+)
- [ ] 10GB EBS volume attached (same AZ)
- [ ] Files copied to instance home directory
- [ ] `chmod +x setup_baxter.sh` executed
- [ ] Script run with `sudo ./setup_baxter.sh` (and completed successfully)
- [ ] Grafana accessible at `http://<INSTANCE_IP>:3000`
- [ ] Dashboards show data (metrics populated)
- [ ] New data files tested via email (auto-ingested to database)

---

**Status:** ✅ Ready for production deployment  
**Setup Time:** ~5–10 minutes  
**Tested On:** Ubuntu 24.04 (AWS EC2)  
**Support:** See README_PAUL_DEPLOYMENT.md for detailed guidance

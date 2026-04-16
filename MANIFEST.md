# 📦 BAXTER DEPLOYMENT PACKAGE — MANIFEST FOR PAUL'S IT TEAM

**Complete solution for deploying Baxter Analytics Pipeline on AWS EC2**

---

## 🎯 What You're Getting

**3 Core Files + 4 Support Documents = Complete Deployment Package**

### Core Files (Required for Setup)
1. **setup_baxter.sh** — Automated deployment script
   - One-command setup for fresh Ubuntu EC2
   - Auto-detects EBS, formats, mounts, installs Docker
   - Deploys 3 services: PostgreSQL, Grafana, Python Ingestor
   - Auto-ingests 97,830+ shipments + 15,456+ claims
   - Time: 5–10 minutes

2. **baxter.env** — Credentials & Configuration Template
   - Fill in Microsoft Graph API credentials (BEFORE deployment)
   - Contains: TENANT_ID, CLIENT_ID, CLIENT_SECRET, MAILBOX_EMAIL, ALLOWED_SENDERS
   - ⚠️ NEVER commit to Git (gitignored automatically)
   - ⚠️ Send separately & securely to IT (not in deployment package)

3. **setup_baxter.sh** — Ready to use, no modification needed
   - Just copy to EC2 instance home directory
   - Script sources credentials from baxter.env at runtime

### Support Documents (Reference & Guidance)
4. **README_PAUL_DEPLOYMENT.md** — Complete Step-by-Step Runbook
   - Prerequisites (Azure AD setup, EC2 provisioning, EBS attachment)
   - 4-step workflow: Prepare → Copy → Run → Verify
   - Troubleshooting section
   - Ongoing operations (email ingestion, logging, backups)
   - **Start here** — Read first, follow instructions

5. **PACKAGE_SUMMARY.md** — Quick 5-Step Overview
   - High-level summary for busy teams
   - Copy-paste SSH commands
   - Minimal but complete

6. **QUICK_REFERENCE_CARD.txt** — Print-Friendly Cheat Sheet
   - 1-page reference for during deployment
   - All key commands at glance
   - Print & keep handy on desk

7. **PRE_DEPLOYMENT_CHECKLIST.md** — Verification Checklist
   - Before starting: verify all prerequisites
   - During deployment: what to expect
   - After deployment: verification steps
   - Sign-off section for deployment team

---

## 📋 Quick Reference Table

| File | Type | Purpose | Before Starting? | During Setup? | After Setup? |
|------|------|---------|-------------------|---------------|--------------|
| **setup_baxter.sh** | Script | Deploy infrastructure | Copy to EC2 | Run on instance | ✅ |
| **baxter.env** | Config | Credentials | **Fill in values** | Sourced by script | ✅ |
| **README_PAUL_DEPLOYMENT.md** | Docs | Full instructions | **Read first** | Reference | Reference |
| **PACKAGE_SUMMARY.md** | Docs | Quick overview | Scan this | Quick ref | ✅ |
| **QUICK_REFERENCE_CARD.txt** | Docs | Cheat sheet | Print/keep nearby | **Use during** | Reference |
| **PRE_DEPLOYMENT_CHECKLIST.md** | Checklist | Verify ready | **Use to verify** | Track progress | **Sign-off** |

---

## 🚀 Getting Started (TL;DR)

### **Before Anything:**
1. Read: [README_PAUL_DEPLOYMENT.md](./README_PAUL_DEPLOYMENT.md) — Full workflow
2. Check: [PRE_DEPLOYMENT_CHECKLIST.md](./PRE_DEPLOYMENT_CHECKLIST.md) — Prerequisites
3. Print: [QUICK_REFERENCE_CARD.txt](./QUICK_REFERENCE_CARD.txt) — Keep handy

### **Prepare (Off AWS):**
```bash
# 1. Complete Azure AD setup (see docs/AZURE_SETUP_GUIDE.html)
#    Get: TENANT_ID, CLIENT_ID, CLIENT_SECRET, MAILBOX_EMAIL

# 2. Edit baxter.env — Replace ALL [PLACEHOLDER] values
#    Fill in your Graph API credentials

# 3. Keep baxter.env safe — Never share publicly, never commit to git
```

### **AWS Setup (In Console):**
```
Launch EC2 Instance:
  ✓ Ubuntu 24.04 LTS
  ✓ Instance type: t3.micro+
  ✓ Root: 20GB gp3
  
Attach EBS Volume:
  ✓ Size: 10GB gp3
  ✓ Same AZ as instance
  ✓ Do NOT format (script will)
  
Enable SSH:
  ✓ Port 22 open to your IP
```

### **Deploy (On Local Machine):**
```powershell
# Copy files to instance
scp -i $KEY -o StrictHostKeyChecking=no `
    setup_baxter.sh baxter.env `
    ubuntu@<INSTANCE_IP>:/home/ubuntu/
```

### **Execute (SSH to Instance):**
```bash
cd ~
chmod +x setup_baxter.sh
sudo ./setup_baxter.sh 2>&1 | tee setup.log

# Wait 5–10 minutes...
# → Grafana ready at http://<IP>:3000
```

### **Verify (Browser):**
```
Navigate to: http://<YOUR_INSTANCE_IP>:3000
Login: admin / admin123

✓ Dashboards load
✓ Data visible (Orders, Claims, $ Saved metrics)
✓ 5 dashboards accessible
```

---

## 📁 File Sizes & Locations

```
deployment-package/
├── setup_baxter.sh                    (12 KB) — Bash script
├── baxter.env                         (2 KB)  — Template with instructions
├── README_PAUL_DEPLOYMENT.md          (25 KB) — Full runbook
├── PACKAGE_SUMMARY.md                 (8 KB)  — Quick overview
├── QUICK_REFERENCE_CARD.txt           (5 KB)  — Cheat sheet
└── PRE_DEPLOYMENT_CHECKLIST.md        (12 KB) — Verification checklist

Total: ~64 KB (very lightweight)
```

---

## ⚙️ What Gets Deployed

### Infrastructure (On EC2)
- **Container Runtime:** Docker + Docker Compose
- **Data Persistence:** EBS volume auto-formatted, mounted at `/data`
- **Services (3 containers):**
  - `baxter_postgres` — PostgreSQL 15 database
  - `baxter_grafana` — Grafana 11.3 dashboards
  - `baxter_ingestor` — Python email polling & data ingestion

### Data (Auto-Ingested)
- **97,830** shipping records (2025-11-19 to 2026-03-13)
- **15,456** customer claims (2025-01-02 to 2026-04-09)
- **267** RMA credits
- **All dashboards pre-configured** with working queries

### Dashboards (Pre-Built, Ready to Use)
1. **Order & Claims Summary** — KPIs, time series, claim breakdown
2. **Volume Over Time** — Trend analysis
3. **Shipment Order Breakdown** — Barcode validation
4. **Claim Validation Detail** — Detailed claim-shipment matching
5. **V2 Summary (VP Dashboard)** — High-level executive view

---

## 🔒 Security & Best Practices

### Credentials Handling
- ✅ `baxter.env` is gitignored (never committed to GitHub)
- ✅ Graph API secrets rotated via Azure AD
- ✅ Database password only accessible inside Docker network
- ✅ Grafana admin password changeable in UI post-deployment

### Data Protection
- ✅ EBS volume mount persists data between reboots
- ✅ PostgreSQL backup recommended (script not included, manual)
- ✅ Ingestor validates file types (only Excel/CSV processed)

### Deployment Safety
- ✅ Script idempotent (safe to run multiple times)
- ✅ EBS auto-detection (won't format if already formatted)
- ✅ Health checks (waits 120s for services to be ready)
- ✅ Logs saved to `setup.log` for troubleshooting

---

## 📞 Support & Troubleshooting

### If Something Goes Wrong
1. **Check setup.log:** `tail -50 setup.log`
2. **Check containers:** `docker ps` (all should show "(healthy)")
3. **Check error:** `cat setup.log | grep ERROR`
4. **Reference:** See "Troubleshooting" section in README_PAUL_DEPLOYMENT.md
5. **Contact:** Share setup.log + specific error with Jahanzeb

### Common Issues & Quick Fixes
| Issue | Fix |
|-------|-----|
| "docker: command not found" | Rerun script (internet may have failed) |
| EBS not detected | Attach 10GB volume in AWS console (same AZ) |
| Grafana "Database error" | Wait 30s, refresh, check `docker logs baxter_postgres` |
| Script timeout | Services booting slow — wait 2 min, refresh Grafana |
| Email not working | Verify Azure AD admin consent (✅ required in Graph permissions) |

---

## 📈 System Requirements

### Minimum (Tested & Verified)
- **OS:** Ubuntu 24.04 LTS or 22.04 LTS
- **Instance:** AWS t3.micro (1 vCPU, 1GB RAM) — tight but works
- **Disk:** 20GB root + 10GB EBS
- **Network:** Outbound internet for Docker pull, email API

### Recommended
- **Instance:** t3.small or t3.medium (better performance)
- **Disk:** 20GB root + 20GB EBS (room for growth)
- **Region:** us-east-2 or your organization's primary region

---

## 🔄 Ongoing Operations (After Setup)

### New Data
- **Email:** Send Excel/CSV to configured mailbox → Auto-processed
- **Manual:** SSH into instance, run manual_upload.py

### Monitoring
- **Logs:** `docker compose logs -f ingestor` (watch ingestion live)
- **Database:** Query tables directly or view via Grafana

### Maintenance
- **Restart Services:** `docker compose restart`
- **Backup Database:** `docker exec baxter_postgres pg_dump ... > backup.sql`
- **Update Credentials:** Edit `/opt/baxter/.env` on instance, restart

---

## 📊 Success Criteria (Post-Deployment)

✅ Deployment Successful When:
- [ ] Script completes without ERROR (OK messages visible)
- [ ] `docker ps` shows 3 containers, all "(healthy)"
- [ ] Grafana loads at `http://<IP>:3000`
- [ ] Dashboards show data:
  - Orders: 6,077+
  - Claims: 1,859+
  - Verified: 63+
  - $ Saved: $123,904+
- [ ] All 5 dashboards accessible
- [ ] No "Data source error" or "No data" messages

---

## 📝 Deployment Logistics

### What's Included
- ✅ One-command setup script
- ✅ Credentials template with instructions
- ✅ Complete runbook (step-by-step)
- ✅ Quick reference card
- ✅ Pre-deployment checklist
- ✅ All dashboards pre-built
- ✅ Historical data (97,830 records) ready to ingest

### What's NOT Included
- ❌ AWS account provisioning (your responsibility)
- ❌ Azure AD setup (detailed guide provided, you complete)
- ❌ SSH key generation (provided separately)
- ❌ Network configuration (beyond basic security group)
- ❌ Ongoing backups (manual script available on request)

---

## 🎓 Learning Resources

- **Docker:** https://docs.docker.com
- **Grafana:** https://grafana.com/docs
- **PostgreSQL:** https://www.postgresql.org/docs
- **AWS EC2:** https://docs.aws.amazon.com/ec2
- **Microsoft Graph API:** https://learn.microsoft.com/en-us/graph

---

## 📅 Version & Timeline

| Date | Event | Status |
|------|-------|--------|
| 2025-11-19 | Initial data (97,830 shipments) | ✅ |
| 2025-01-02 | Claims data begins | ✅ |
| 2026-03-13 | Historical data cutoff | ✅ |
| 2026-04-16 | Deployment package complete | ✅ Production Ready |

---

## 🎯 Next Steps for Paul's IT Team

1. **Download all files** from GitHub or deployment package
2. **Read README_PAUL_DEPLOYMENT.md** (30 min read)
3. **Print QUICK_REFERENCE_CARD.txt** (reference during deploy)
4. **Use PRE_DEPLOYMENT_CHECKLIST.md** (verify before starting)
5. **Follow 4-step workflow** (prepare → copy → run → verify)
6. **Go live** (Grafana ready in 5–10 min)

---

## 📞 Support

**Questions or Issues?**
- Check PRE_DEPLOYMENT_CHECKLIST.md troubleshooting section
- Review setup.log for error details
- Contact Jahanzeb with setup.log + error screenshot

**Ready to Deploy?**
→ Start with README_PAUL_DEPLOYMENT.md

---

**Package Version:** 1.0  
**Date:** April 16, 2026  
**Status:** ✅ Production Ready for Paul's Deployment

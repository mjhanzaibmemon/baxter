# Pre-Deployment Checklist — Baxter Pipeline

**Use this checklist to verify all prerequisites before running setup_baxter.sh**

---

## 🔐 CREDENTIALS (Complete First)

### Azure AD Setup
- [ ] Visited [docs/AZURE_SETUP_GUIDE.html](./docs/AZURE_SETUP_GUIDE.html)
- [ ] App Registration created in Azure Portal
- [ ] Application (Client) ID copied
- [ ] Directory (Tenant) ID copied
- [ ] Client Secret created and saved **immediately** (only shown once!)
- [ ] API Permissions added:
  - [ ] `Mail.Read` — Application permission
  - [ ] `Mail.ReadWrite` — Application permission
- [ ] **Admin consent granted** (green ✅ checkmarks visible in Azure Portal)
- [ ] Mailbox email determined (e.g., `logistics@baxter.com`)
- [ ] Approved sender email list prepared (comma-separated)

### baxter.env Credentials
- [ ] Opened `baxter.env` in text editor
- [ ] **All [PLACEHOLDER] values replaced** (no remaining brackets):
  - [ ] `GRAPH_TENANT_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"`
  - [ ] `GRAPH_CLIENT_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"`
  - [ ] `GRAPH_CLIENT_SECRET="NEs8Q~..."`
  - [ ] `MAILBOX_EMAIL="email@company.com"`
  - [ ] `ALLOWED_SENDERS="email1@company.com,email2@company.com"`
- [ ] File saved

---

## 🖥️ AWS INFRASTRUCTURE

### EC2 Instance
- [ ] Ubuntu 24.04 or 22.04 LTS launched
- [ ] Instance type: `t3.micro` or larger
- [ ] Root volume: 20GB (gp3 minimum)
- [ ] **Instance IP/Hostname noted:** `ec2-XXX-XXX-XXX.us-east-2.compute.amazonaws.com`
- [ ] Instance in **running** state (green light)
- [ ] Security group allows SSH (TCP port 22 from your IP)

### EBS Volume
- [ ] 10GB EBS volume created (gp3 recommended)
- [ ] Volume in **available** state
- [ ] **In SAME Availability Zone** as EC2 instance
- [ ] Attached to EC2 instance as `/dev/nvme1n1` or similar (check in EC2 console)
- [ ] ⚠️ **NOT formatted** — script will format as ext4

### Network & Access
- [ ] Can SSH into instance: `ssh -i /path/to/key.pem ubuntu@<INSTANCE_IP>`
- [ ] Instance has outbound internet (can `ping google.com` from instance)
- [ ] SSH key file is accessible and has correct permissions (chmod 600)

---

## 📁 LOCAL FILES (On Your Workstation)

### File Preparation
- [ ] Folder created for deployment (e.g., `C:\Users\YourName\Desktop\baxter-deploy`)
- [ ] `setup_baxter.sh` copied to folder
- [ ] `baxter.env` copied to folder and **all credentials filled in**
- [ ] `README_PAUL_DEPLOYMENT.md` copied to folder (reference)
- [ ] `QUICK_REFERENCE_CARD.txt` copied to folder (print for reference)

### File Verification
- [ ] `setup_baxter.sh` is readable and not corrupted (>300KB)
- [ ] `baxter.env` contains all credential values (not [PLACEHOLDER] text)
- [ ] Both files are in same folder ready to copy to EC2

---

## 🚀 PRE-FLIGHT (Before Running Script)

### SSH Access
- [ ] SSH key file accessible (e.g., `C:\Users\...\Downloads\rdp.pem`)
- [ ] SSH key has correct permissions and format
- [ ] Can SSH into instance without password: 
  ```bash
  ssh -i /path/to/key ubuntu@<INSTANCE_IP>
  ```
- [ ] Connected to instance and can see `$` prompt

### Instance State
- [ ] Instance is fully booted (check AWS console, status checks: ✅ 2/2 passed)
- [ ] 1–2 minutes have passed since instance launched
- [ ] No pending EBS volume formatting (EBS shown as "attached")
- [ ] Instance security group allows SSH inbound

### Files on Instance
- [ ] `scp` command executed successfully (no errors)
- [ ] Files visible on instance: `ls -lah ~/setup_baxter.sh ~/baxter.env`
  - Should show both files, ~500+ KB total
- [ ] `baxter.env` is **readable**: `cat ~/baxter.env | head -5`
- [ ] No permission denied errors

---

## ✅ LAUNCH READINESS

### Before Running Script
- [ ] You have ~10 minutes available (do not interrupt script)
- [ ] Instance is in us-east-2 or your target region
- [ ] EBS volume still shows as "attached" in AWS console
- [ ] All credentials in `baxter.env` are correct (copy-paste verified, no typos)
- [ ] Script file has correct permissions:
  ```bash
  chmod +x ~/setup_baxter.sh
  ```

### Final Confirmation
- [ ] Ran: `cat ~/setup_baxter.sh | head -20` → Shows bash script (not binary)
- [ ] Ran: `cat ~/baxter.env | grep GRAPH_TENANT_ID` → Shows your actual UUID (not [PLACEHOLDER])
- [ ] Ready to execute: `sudo ./setup_baxter.sh`

---

## 📊 DEPLOYMENT (During Script Execution)

### Script Running
- [ ] Initiated: `sudo ./setup_baxter.sh 2>&1 | tee setup.log`
- [ ] Output starts immediately (blue [INFO] messages appear)
- [ ] See colored output ✅ OK (green), ⚠️ WARN (yellow), ❌ ERROR (red)

### What to Expect (in order)
- [ ] Step 0: EBS formatting or mount check
- [ ] Step 1: System package updates
- [ ] Step 2: Base packages install (git, curl)
- [ ] Step 3: Docker install + version check
- [ ] Step 4: Repository clone/pull
- [ ] Step 5: .env file created
- [ ] Step 6: `docker compose up -d --build` (containers start)
- [ ] Step 7: Health checks (wait ~60–90 seconds)
- [ ] Step 8: Auto-ingest data files (should show file names being processed)
- [ ] **Done:** Final success message with Grafana URL

### If Script Fails
- [ ] **Do NOT** immediately restart — check `setup.log` first
- [ ] Check error message:
  ```bash
  tail -50 setup.log
  cat setup.log | grep ERROR
  ```
- [ ] Consult troubleshooting section in `README_PAUL_DEPLOYMENT.md`
- [ ] If unsure, contact support with full `setup.log` contents

---

## 🎯 POST-DEPLOYMENT VERIFICATION

### Immediate (After Script Completes)

**Container Status**
- [ ] Ran: `docker ps`
- [ ] See 3 containers: `baxter_postgres`, `baxter_grafana`, `baxter_ingestor`
- [ ] All show status: `Up X minutes (healthy)`
- [ ] No containers in `Exited` state

**Database Check**
- [ ] Ran: `sudo docker exec baxter_postgres psql -U baxter -d baxter_demo -c "SELECT COUNT(*) FROM shipments;"`
- [ ] Output shows: `97830` (indicates data loaded)
- [ ] No errors or connection refused

**Grafana Access (Browser)**
- [ ] Navigated to: `http://<YOUR_INSTANCE_IP>:3000`
- [ ] Page loads (no connection timeout)
- [ ] Login page visible
- [ ] Logged in with: `admin` / `admin123`
- [ ] Dashboard loads (no "Data source error")

### Dashboards Visible

**Main Dashboard (Order & Claims Summary)**
- [ ] Panel: "Orders Shipped" shows ~6,077
- [ ] Panel: "Claims Submitted" shows ~1,859
- [ ] Panel: "Verified Shortages" shows ~63
- [ ] Panel: "$ Saved" shows ~$123,904.87
- [ ] Bar chart and table visible (no "No data" messages)

**Other Dashboards**
- [ ] Can navigate between 5 dashboards (dropdown or menu)
- [ ] Volume Over Time shows data
- [ ] Shipment Breakdown loads
- [ ] Claim Validation Detail shows records
- [ ] V2 Summary shows KPIs

### Data Validation
- [ ] Database has 97,830+ shipment rows
- [ ] Database has 15,456+ claim rows
- [ ] Grafana queries completing without timeout
- [ ] All date ranges showing expected data

---

## 🔧 OPERATIONAL READINESS

### Email Ingestion
- [ ] Any new Excel files sent to `MAILBOX_EMAIL` will be auto-processed
- [ ] Ingestor logs show: `Checking mailbox every X minutes`
- [ ] Check logs: `sudo docker compose -f /opt/baxter/docker-compose.yml logs -f ingestor`

### Data Persistence
- [ ] EBS mount confirmed: `df -h | grep /data`
- [ ] Should show `/dev/nvme1n1` mounted at `/data` (or `/dev/xvdb`)
- [ ] Size should be ~10GB

### Backup Ready
- [ ] Documented instance ID and EBS volume ID (for future snapshots)
- [ ] Noted `baxter.env` location for future redeploys

---

## 📝 SIGN-OFF

**Deployment completed successfully on:**

| Item | Value |
|------|-------|
| Date | _____________ |
| Instance IP | _____________ |
| Instance ID | _____________ |
| EBS Volume ID | _____________ |
| Grafana URL | `http://_____________:3000` |
| Authorized By | _____________ |

**All checks passed:** ☐ YES ☐ NO

**If NO, list issues below:**

```
1. _________________________________________________________________
2. _________________________________________________________________
3. _________________________________________________________________
```

---

## 📞 NEXT STEPS

- [ ] Document instance details for operations team
- [ ] Set up monitoring/alerts (optional)
- [ ] Test new data file ingestion (send sample Excel to mailbox)
- [ ] Schedule regular backups (EBS snapshot policy recommended)
- [ ] Review Grafana dashboard metrics weekly with stakeholders

---

**Checklist Version:** 1.0  
**Last Updated:** April 16, 2026  
**Print & Keep With Deployment Records**

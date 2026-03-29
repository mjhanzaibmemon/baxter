# Project Context: Baxter Shipping & Claims Dashboard

## Project Overview
- **Purpose:**
  - This system ingests, stores, and visualizes Baxter's shipping and claims data for operational and business analytics.
  - Provides real-time dashboards for Orders Shipped, Claims Submitted, Verified Shortages, and $ Saved, with breakdowns and trends for business users.

---

## Current Architecture & Services
- **Cloud Platform:**
  - AWS EC2 (t2.micro instance for cost efficiency)
- **Containers & Orchestration:**
  - Docker Compose manages services (PostgreSQL, Grafana, Python ingestor, etc.)
- **Database:**
  - PostgreSQL (initialized with `postgres/init.sql`)
- **Dashboards:**
  - Grafana (JSON dashboards in `grafana/dashboards/`)
## Data Ingestion Pipeline (Ingestor Service)

### How It Works
1. **Email Polling** → Ingestor service checks a configured mailbox for new attachments
2. **File Detection** → Supports Excel (`.xlsx`) and CSV (`.csv`) formats
3. **Deduplication** → Uses content hash (SHA256) to prevent duplicate file processing
4. **Parsing** → `excel_parser.py` extracts data from shipments, RMA credits, and claim details
5. **Database Insert** → `db.py` inserts data into PostgreSQL tables with proper normalization
6. **Email Alerts** → Sends success/error notifications back to the user

### Status (March 2026)
- **Service:** Running as Docker container `baxter_ingestor`
- **Data Flow:** Email → Attachment → Parse → Hash Check → Insert DB → Dashboard Update
- **Latest Data:** As of March 29, 2026, database contains:
  - 70,323 distinct order IDs in shipments
  - 14,774 claims
  - 5,070 claims with matching business_unit_codes
- **Frequency:** Scheduled via APScheduler for periodic checks (configurable interval)

### Key Files
- `ingestor/main.py` — Entry point with APScheduler and ingestion cycle logic
- `ingestor/graph_api.py` — Email polling (Microsoft Graph or similar)
- `ingestor/excel_parser.py` — File parsing logic
- `ingestor/db.py` — Database insert and deduplication logic
- `ingestor/requirements.txt` — Python dependencies

### Data Continues to Flow
✅ Yes, the ingestor service is still active and running. New emails with attachments will be automatically:
- Checked for duplicates (won't re-insert same file twice)
- Parsed and inserted into the database
- Reflected in Grafana dashboards within the next 5-minute refresh cycle

No manual intervention needed unless the service crashes or email credentials change.

---

## Configurations & Setup Done So Far
- **Database:**
  - PostgreSQL container set up and seeded with sample data
  - Functional indexes and optimized queries for t2.micro performance
- **Grafana:**
  - Configured to use PostgreSQL as the data source
  - Dashboards use variables (`carrier`, `claim_type`) and time filters (`$__timeFilter`)
  - Panels styled with color backgrounds, stat/graph/bar chart types, and customer breakdowns
- **Codebase:**
  - Python ingestor scripts for data loading and transformation
  - All dashboard JSONs versioned in GitHub
- **Deployment:**
  - Git workflow: local changes → commit/push to GitHub → pull on EC2 → restart Grafana
- **Environment Variables:**
  - Database credentials, Grafana admin password, etc., are set in Docker Compose `.env` or as container environment variables (see `docker-compose.yml`)

---

## Issues Discussed & Solutions
- **Dashboard Data Verification:**
  - Verified all dashboard numbers directly from the database using SQL queries
  - Ensured all metrics (Orders Shipped, Claims Submitted, etc.) match between DB and Grafana
- **Performance & Cost:**
  - Optimized queries and indexes to run efficiently on t2.micro
  - Confirmed that the system runs within AWS free tier/low-cost limits
- **Dashboard Consistency:**
  - Reviewed all existing dashboard JSONs and queries to ensure formulas and data sources are consistent
  - Used working dashboards as reference for all new panels and queries
- **Summary Dashboard Creation:**
  - Created a new summary dashboard (`00_summary_dashboard.json`) matching the style, queries, and layout of the reference image and existing dashboards
  - Used exact queries and color conventions from production dashboards
- **Deployment Workflow:**
  - Standardized process: push to GitHub, pull on EC2, restart Grafana, verify in UI

---

## Completed Dashboards (March 29, 2026)

### 1. **00_summary_dashboard.json** ✅ LIVE
- **Metrics:** Orders Shipped (6,077), Claims Submitted (1,859), Verified Shortages (90), $ Saved ($185,716.79)
- **Features:** Month-over-month percent changes, weekly trend chart, customer breakdown bar chart, bottom total stat
- **Queries:** Cumulative month-over-month with realistic percent changes (10.4%, 2.37%, 23.3%, 13.9%)
- **Status:** All values verified against database. Deployed to EC2. Auto-refreshes every 5 minutes.
- **Latest commit:** `3ca90e7` - "Fix percent change: use month-over-month comparison instead of cumulative"

### 2. **01_volume_over_time.json** ✅
- Shipment and claim volume trends

### 3. **02_shipment_order_breakdown.json** ✅
- Barcode validation with Order ID and SSCC18 filters

### 4. **04_claim_validation.json** ✅
- Complex claim matching with customer breakdowns
- **Note:** This dashboard took significantly more development hours than scoped due to cross-database matching logic and troubleshooting

## Data Verification Results (March 2026)
- **Orders Shipped:** 6,077 (DB verified)
- **Claims Submitted:** 1,859 (DB verified)
- **Verified Shortages:** 90 (DB verified via SSCC18 + Order ID matching)
- **$ Saved:** $185,716.79 (DB verified)
- **Date Range:** 2025-01-01 to 2026-03-29, with filters for carriers (FXFE, HSNR, HSND, HSNC, HSNN, HSNA) and claim type (SHORTAGE)

## Current Tasks & Next Steps
- **Current Status:** All 4 dashboards live and operational
- **Next Steps:**
  1. Monitor dashboard performance and user feedback from Paul
  2. Plan Phase 2 features (KPI alerts, mobile views, additional drill-down reports)
  3. Consider expanding scope based on client requirements

---

## Secrets, Keys, and Credentials

### EC2 Access (ACTIVE)
- **EC2 Public IP:** `ec2-18-219-216-17.us-east-2.compute.amazonaws.com`
- **SSH Key Location:** `$env:USERPROFILE\Downloads\rdp.pem` (Windows)
- **SSH Command:**
  ```
  ssh -i "$env:USERPROFILE\Downloads\rdp.pem" ubuntu@ec2-18-219-216-17.us-east-2.compute.amazonaws.com
  ```
- **EC2 Project Path:** `/home/ubuntu/baxter`
- **Deployment Command (from EC2):**
  ```
  cd /home/ubuntu/baxter && git pull && docker compose restart grafana
  ```

### Database Credentials
- **Host:** `postgres` (Docker container name, or `localhost:5432` from host)
- **Database:** `baxter_demo`
- **Username:** `baxter`
- **Password:** `baxter_secret_123` (set in docker-compose.yml)
- **Grafana Datasource UID:** `PCC52D03280B7034C` (auto-assigned by Grafana)

### Grafana Access
- **URL:** EC2 Grafana (port 3000, typically via Docker)
- **Admin Username:** `admin`
- **Admin Password:** `admin123` (set in docker-compose.yml)

### GitHub Repository
- **Repo URL:** `https://github.com/mjhanzaibmemon/baxter.git`
- **Branch:** `main`
- **Latest Commit:** `3ca90e7` (Summary dashboard percent fix)

### Docker Services
- **Grafana Container:** `baxter_grafana`
- **PostgreSQL Container:** `baxter_postgres`
- **Ingestor Container:** `baxter_ingestor`
- **Command:** `docker compose ps` (to list all running services)

---

## Old Credentials (TEMPLATE - DO NOT USE)
- **EC2 SSH Key:**
  - Placeholder: `~/keys/baxter-ec2.pem` (local machine)
  - Usage: `ssh -i ~/keys/baxter-ec2.pem ec2-user@<EC2_PUBLIC_IP>`
  - Never commit PEM files to GitHub. Store in a secure location (local disk, 1Password, etc.)
- **Database Credentials:**
  - Placeholder: Set in Docker Compose `.env` file or as environment variables
  - Example: `POSTGRES_PASSWORD=your_db_password` (do not commit real passwords)
  - Usage: Used by both Grafana and Python ingestor containers
- **Grafana Admin Password:**
  - Placeholder: Set in Docker Compose `.env` or as environment variable
  - Example: `GF_SECURITY_ADMIN_PASSWORD=your_grafana_password`
  - Usage: Needed for first-time Grafana login

---

## Environment Variables & File Locations
- `.env` file (root or in `ingestor/`): stores DB, Grafana, and other service credentials
- `~/keys/baxter-ec2.pem`: EC2 SSH key (local only)
- `docker-compose.yml`: references all environment variables and service configs
- `grafana/dashboards/`: all dashboard JSONs
- `ingestor/`: Python scripts for data ingestion
- `postgres/`: DB initialization scripts

---

**This file must be updated with any new changes, issues, or architectural decisions to ensure full project continuity.**

**If you need to access the EC2 instance, always use the SSH key at the documented path. For any new secrets, update this file with the placeholder and storage location.**

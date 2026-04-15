# Project Context: Baxter Shipping & Claims Dashboard
# COMPREHENSIVE CONTEXT — Updated April 15, 2026
# This file contains EVERYTHING needed for a new AI session to continue this project.

---

## CLIENT INFORMATION
- **Client Name:** Paul (Baxter Healthcare / Baxter International)
- **Platform:** Upwork
- **Client Role:** Paul works in supply chain/logistics at Baxter. Reports to a VP who has seen and approved the dashboards.
- **Relationship Status:** EXCELLENT. Paul verified all data personally (took him 2 hours), said "100% spot on" and "Couldn't be happier with your deliverables!" VP loved it too.
- **Communication Style:** Paul is direct, knowledgeable about shipping/logistics, asks good questions, and verifies data himself. Very engaged client.
- **Project Status:** ONGOING — Paul wants to keep the project alive, will send updated data files bi-weekly.
- **Milestone 9:** "Additional Screen" (V2 Dashboard) — $450 APPROVED by Paul (April 15)
- **Milestone 10:** "Additional screen visual review and data validation" — $450 active, due April 25
- **Paul's AWS Server:** Baxter-managed, private network, no public IP/SSH. Access via internal VPN + RDP only. Paul's IT working on Docker approval. Plan: deployment script that IT runs.

---

## PROJECT OVERVIEW
- **Purpose:** System that ingests, stores, and visualizes Baxter's shipping and claims data to identify false shortage claims from customers and calculate recoverable money ($ Saved).
- **Business Logic:** Customers (distributors like McKesson, Amerisourcebergen, Cardinal Health, Owens & Minor) file shortage claims saying they didn't receive full orders. Baxter cross-references these claims against their shipment records. If ALL LPNs (packages) were scanned and the order was delivered "Perfect", the claim is FALSE and Baxter can recover that money.
- **Key Insight (from Paul, March 30 2026):** Only claims where Order Status = "Perfect" count as recoverable ($ Saved). Claims where Order Status = "Short" mean Baxter's records also show the order was short — so Baxter can't dispute those.

---

## CURRENT ARCHITECTURE & SERVICES
- **Cloud Platform:** AWS EC2 (Ubuntu, t2.micro)
- **Containers:** Docker Compose manages 3 services:
  1. `baxter_grafana` — Grafana v11.3.0 (dashboards)
  2. `baxter_postgres` — PostgreSQL 15-alpine (database)
  3. `baxter_ingestor` — Python ingestor (email polling + data ingestion)
- **Database:** PostgreSQL (initialized with `postgres/init.sql`)
- **Dashboards:** Grafana (JSON dashboards in `grafana/dashboards/`)
- **Web Server:** Nginx installed on EC2 for serving HTML documentation
- **GitHub:** All code versioned at `https://github.com/mjhanzaibmemon/baxter.git` (branch: main)
## Data Ingestion Pipeline (Ingestor Service)

### How It Works
1. **Email Polling** → Ingestor service checks a configured mailbox for new attachments
2. **File Detection** → Supports Excel (`.xlsx`) and CSV (`.csv`) formats
3. **Deduplication** → Uses content hash (SHA256) to prevent duplicate file processing
4. **Parsing** → `excel_parser.py` extracts data from shipments, RMA credits, and claim details
5. **Database Insert** → `db.py` inserts data into PostgreSQL tables with proper normalization
6. **Email Alerts** → Sends success/error notifications back to the user

### Status (April 2026)
- **Service:** Running as Docker container `baxter_ingestor`
- **Data Flow:** Email → Attachment → Parse → Hash Check → Insert DB → Dashboard Update
- **Latest Data:** As of April 15, 2026, database contains:
  - 97,830 shipment rows
  - 15,456 claims (date range: 2025-01-02 to 2026-04-09)
  - 267 RMA credits
- **Frequency:** Scheduled via APScheduler for periodic checks (configurable interval)

### Key Files
- `ingestor/main.py` — Entry point with APScheduler and ingestion cycle logic
- `ingestor/graph_api.py` — Email polling (Microsoft Graph or similar)
- `ingestor/excel_parser.py` — File parsing logic
- `ingestor/db.py` — Database insert and deduplication logic
- `ingestor/requirements.txt` — Python dependencies

### Supported File Types
| File Type | Detection Pattern | Parser Function | DB Function |
|---|---|---|---|
| MS_Kargo Excel | `ms_kargo` or `kargo` in filename | `parse_ms_kargo()` | `insert_shipments()` |
| Result CSV | `.csv` with `result` or `shipment` in filename | `parse_result_csv()` | `insert_shipments()` |
| AllOrders CSV | `allorders` or `all_orders` in filename | `parse_all_orders_csv()` | `update_order_status()` |
| CS_RMA Excel | `cs_rma` or `rma` in filename | `parse_rma_detail()` + `parse_rma_data_sheet()` | `insert_rma_credits()` + `insert_claim_details()` |
| **Kargo Order Level CSV** | `order_level` in filename | `parse_order_level_csv()` | `update_kargo_order_status()` |

### Kargo Order Level Mapping (IMPORTANT)
- Kargo scan files have 16-digit `orderNumber` = first 8 digits (shipment prefix) + remaining digits (original order number)
- Parser strips first 8 digits to get original order for DB matching
- `orderStatus`: COMPLETED → Perfect, INCOMPLETE → Short
- `missedLpns`: pipe-delimited SSCC18 values (packages Kargo missed scanning)
- DB matching: tries exact `order_id` match first, then `RIGHT(order_id, N)` fallback

### Data Continues to Flow
✅ Yes, the ingestor service is still active and running. New emails with attachments will be automatically:
- Checked for duplicates (won't re-insert same file twice)
- Parsed and inserted into the database
- Reflected in Grafana dashboards within the next 5-minute refresh cycle

No manual intervention needed unless the service crashes or email credentials change.

---

## ACCESS & CREDENTIALS (ALL ACTIVE)

### EC2 Access
- **EC2 Public DNS:** `ec2-18-219-216-17.us-east-2.compute.amazonaws.com`
- **Region:** us-east-2
- **SSH Key Location:** `$env:USERPROFILE\Downloads\rdp.pem` (Windows)
- **SSH Command (PowerShell):**
  ```
  ssh -i "$env:USERPROFILE\Downloads\rdp.pem" ubuntu@ec2-18-219-216-17.us-east-2.compute.amazonaws.com
  ```
- **EC2 Project Path:** `/home/ubuntu/baxter`
- **OS:** Ubuntu

### Database Credentials
- **Host:** `postgres` (Docker internal) or `localhost:5432` (from EC2 host)
- **Database:** `baxter_demo`
- **Username:** `baxter`
- **Password:** `baxter_secret_123`
- **Grafana Datasource UID:** `PCC52D03280B7034C`

### Grafana Access
- **URL:** `http://ec2-18-219-216-17.us-east-2.compute.amazonaws.com:3000`
- **Admin Username:** `admin`
- **Admin Password:** `admin123`

### Documentation URLs (Nginx on port 80)
- `http://ec2-18-219-216-17.us-east-2.compute.amazonaws.com/docs/AZURE_SETUP_GUIDE.html`
- `http://ec2-18-219-216-17.us-east-2.compute.amazonaws.com/docs/BAXTER_DOCUMENTATION.html`

### GitHub Repository
- **Repo URL:** `https://github.com/mjhanzaibmemon/baxter.git`
- **Branch:** `main`
- **Latest Commit:** `6f89bac` — "$ Saved shows only Perfect orders (recoverable), rename Valid Claim to Order Scanned"

### Docker Services
- **Grafana:** `baxter_grafana`
- **PostgreSQL:** `baxter_postgres`
- **Ingestor:** `baxter_ingestor`
- **IMPORTANT:** Use `docker compose` (NOT `docker-compose`) — service names are `grafana`, `postgres`, `ingestor` (not container names)
- **Commands:**
  ```
  docker compose ps                    # List services
  docker compose restart grafana       # Restart Grafana
  docker compose logs -f ingestor      # Check ingestor logs
  ```

---

## DEPLOYMENT PROCESS (How to deploy changes)

### From Local (Windows PowerShell):
```
# 1. Edit files locally in: C:\Users\MUHAMMAD JAHANZEB\Desktop\paul-demo-pipeline

# 2. Upload to EC2:
scp -i "$env:USERPROFILE\Downloads\rdp.pem" grafana/dashboards/00_summary_dashboard.json ubuntu@ec2-18-219-216-17.us-east-2.compute.amazonaws.com:/home/ubuntu/baxter/grafana/dashboards/

# 3. Restart Grafana:
ssh -i "$env:USERPROFILE\Downloads\rdp.pem" ubuntu@ec2-18-219-216-17.us-east-2.compute.amazonaws.com "cd /home/ubuntu/baxter && docker compose restart grafana"

# 4. Git commit:
git add .; git commit -m "message"; git push
```

### CRITICAL: PowerShell Escaping Issues
- Complex SQL with `$`, quotes, `<>` BREAKS in PowerShell terminal
- **Solution:** Use Python script to generate/modify JSON files, then delete the script
- For SQL queries via SSH, use PowerShell here-strings:
  ```powershell
  $q = @"
  SELECT ... your SQL here ...
  "@
  $q | ssh -i "$env:USERPROFILE\Downloads\rdp.pem" ubuntu@... "docker exec -i baxter_postgres psql -U baxter -d baxter_demo"
  ```

---

## DATABASE DETAILS

### Tables
- **shipments** — Shipping/delivery records with order_id, sscc18, scac (carrier code), appointment_date, order_status (Perfect/Short), etc.
- **claim_details** — Customer shortage claims with order_id, sscc18, claim_date, claim_type, claim_amount, ship_to_name, address_name, contact_name, item_number, quantity, unit_of_measure, business_unit_code, etc.

### Data Stats (as of April 15, 2026)
- **Shipments:** 97,830 rows (date range: 2025-11-19 to 2026-03-13)
- **Claims:** 15,456 total (date range: 2025-01-02 to 2026-04-09)
- **RMA Credits:** 267 rows
- **Carriers (SCAC codes):** FXFE, HSNR, HSND, HSNC, HSNN, HSNA
- **Business Unit Codes filter:** '1MF','1MY','1MQ','1MS','1MK'

### Claim Matching Logic (CRITICAL — This is the core algorithm)
A claim is "verified" (matched to a shipment) if:
1. **SSCC18 match:** claim's sscc18 matches a shipment's sscc18, OR
2. **Order ID match:** claim's order_id matches LAST 7 or 8 digits of a shipment's order_id

SQL pattern used everywhere:
```sql
EXISTS(SELECT 1 FROM shipments s 
  WHERE s.scac IN (carrier_list)
  AND s.order_status = 'Perfect'   -- ONLY for $ Saved/recoverable queries
  AND ((c.sscc18 IS NOT NULL AND c.sscc18 <> '' AND s.sscc18=c.sscc18) 
    OR (c.order_id IS NOT NULL AND c.order_id <> '' 
      AND ((LENGTH(c.order_id) = 7 AND RIGHT(s.order_id, 7) = c.order_id) 
        OR (LENGTH(c.order_id) = 8 AND RIGHT(s.order_id, 8) = c.order_id)))))
```

### Valid Claim + Order Status Combinations (Verified March 30, 2026)
| Valid Claim (now "Order Scanned") | Order Status | Claims | Amount |
|---|---|---|---|
| **Yes** | **Perfect** | **49→63** | **$109,575→$123,905** |
| Yes | Short | 37 | $74,648 |
| Yes | - (unknown) | 4 | $1,494 |
| No | - | 1,765 | $4,157,071 |
| No | Perfect | 3 | $92,207 |
| No | Short | 1 | $1,301 |

**NOTE:** The numbers changed from 49→63 and $109K→$123K because the EXISTS with Perfect filter matches differently than the grouped counts. The live verified numbers from the dashboard are: **63 claims, $123,904.87**

---

## 5 DASHBOARDS — DETAILED STATUS

### Dashboard 1: `00_summary_dashboard.json` — "Order & Claims Summary" ✅ LIVE
**This is the MAIN dashboard that Paul sees.**

**Panels (7 + 1 table = 8 total):**

1. **Orders Shipped** (stat, blue background) — `COUNT(DISTINCT order_id) FROM shipments`
   - Shows: 6,077 | +10.4%
   - Uses month-over-month percent change (showPercentChange: true)

2. **Claims Submitted** (stat, orange background) — `COUNT(*) FROM claim_details`
   - Shows: 1,859 | +2.37%
   - Filters: business_unit_code IN ('1MF','1MY','1MQ','1MS','1MK'), claim_type = SHORTAGE

3. **Verified Shortages** (stat, green background) — COUNT of claims matching shipments WHERE order_status = 'Perfect'
   - Shows: **63** | percent change shown
   - **IMPORTANT:** Only counts Perfect orders (changed March 30 per Paul's request)

4. **$ Saved** (stat, green background, top right) — SUM(ABS(claim_amount)) WHERE matched AND order_status = 'Perfect'
   - Shows: **$123,904.87** (was $185K before Perfect filter)
   - Unit: currencyUSD, 2 decimals

5. **Orders Shipped and Claims Submitted Over Time** (timeseries, weekly bars)
   - Dual y-axis: Orders (left, blue bars), Claims (right, orange bars)
   - Grouped by `date_trunc('week')`

6. **Verified vs Invalid Claims by Customer** (horizontal stacked bar chart)
   - Green = Verified, Red = Invalid
   - Top 7 customers by claim count

7. **$ Saved from Verified Shortages** (stat, bottom center)
   - Same query as panel 4 but different format (no percent change, larger display)

8. **Verified Shortage Details** (table, bottom) — **ADDED March 30**
   - Columns: Customer, Order Number, Shortage $
   - Shows individual orders (NOT grouped by customer)
   - Only shows claims where order_status = 'Perfect'
   - Sorted by shortage amount DESC
   - Footer shows SUM of Shortage $ column
   - 63 rows currently

**Template Variables:**
- `DS_POSTGRESQL` — Datasource (type: datasource, query: postgres)
- `order_id` — Textbox filter
- `sscc18` — Textbox filter
- `carrier` — Multi-select from `SELECT DISTINCT scac FROM shipments` (defaults: FXFE, HSNR, HSND, HSNC, HSNN, HSNA)
- `claim_type` — Multi-select from `SELECT DISTINCT claim_type FROM claim_details WHERE claim_type NOT ILIKE '%missing%pro%'` (default: SHORTAGE)

**Percent Change Logic:**
- Each stat panel uses time_series format with 2 data points:
  - Point 1 (previous): data from $__timeFrom() to start of current month
  - Point 2 (current): data from $__timeFrom() to now
  - Grafana compares last vs previous for % change

### Dashboard 2: `01_volume_over_time.json` ✅ LIVE
- Shipment and claim volume trends over time

### Dashboard 3: `02_shipment_order_breakdown.json` ✅ LIVE
- Barcode validation with Order ID and SSCC18 filters

### Dashboard 4: `04_claim_validation.json` — "Grafana Detailboard" ✅ LIVE
**This is the DETAILED claim validation dashboard.**

**Panels:**
1. Orders Shipped (stat)
2. Claims Submitted (stat)
3. Verified Shortages (stat)
4. Invalid Claims (stat, red)
5. Claim & Shortage Rate Over Time (timeseries, line chart)
6. Claims by Customer (horizontal stacked bar chart)
7. Claim Validation Details (TABLE — main feature)
   - Columns: Order, Ship To, Contact Name, Item Number, Qty Ordered, UM, SSCC18, **Order Scanned** (was "Valid Claim"), Order Status, Notes
   - "Order Scanned" shows ✔ Yes / ✘ No with row color coding (green/red)
   - Notes column shows "Matched by SSCC18", "Matched by Order ID", or "No Matching Shipment"

**RENAME (March 30):** "Valid Claim" → "Order Scanned" per Paul's request. Paul felt "Order Scanned" better describes whether all LPNs were scanned/read.

### Dashboard 5: `05_v2_summary_dashboard.json` — "Monthly Claims Performance & Kargo Validation (V2)" ✅ LIVE
**VP-friendly "dumbed down" summary screen. Created April 2026 for Paul's VP.**

**Panels (13 total):**
1. **Subtitle** (text/html) — "Monthly Claims Performance — Dynamic Date Range"
2. **Claims Received** (stat) — COUNT of claims in period
3. **Would Have Paid (Before Validation)** (stat) — SUM(ABS(claim_amount)) for all matched claims
4. **Refutable Claims (Kargo "Perfect Match")** (stat) — COUNT where order_status = 'Perfect'
5. **Avoidable Spend (Kargo Verified)** (stat) — SUM(ABS(claim_amount)) where Perfect match
6. **Actually Paid** (stat) — Total claims minus Kargo-verified amount
7. **What We Paid vs. What We Should Have Paid** (stacked bar chart)
8. **Kargo Validation Coverage** (gauge) — % of claims with Kargo match
9. **Claims Trend: Received vs. Refutable** (line chart, monthly)
10. **Monthly Summary** (table) — Month, Claims, $, Refutable, Avoidable $
11. **⚠ Missed Opportunities** (text) — SQL-driven missed savings callout
12. **Key Takeaway** (text) — Dynamic insight text
13. **Bottom Line** (text) — Banner with savings summary

**UID:** `summary-dashboard-v2`
**Time Range:** `now-3M`
**Same template variables as Dashboard 1** (carrier, claim_type, order_id, sscc18)

---

## DATA INGESTION PIPELINE

### How It Works
1. **Email Polling** → Ingestor checks a configured mailbox for new attachments
2. **File Detection** → Supports Excel (.xlsx) and CSV (.csv)
3. **Deduplication** → SHA256 content hash prevents duplicate processing
4. **Parsing** → `excel_parser.py` extracts shipments, RMA credits, claim details
5. **Database Insert** → `db.py` inserts into PostgreSQL with normalization
6. **Email Alerts** → Sends success/error notifications

### Key Files
- `ingestor/main.py` — Entry point, APScheduler, `run_ingestion_cycle()` function
- `ingestor/graph_api.py` — Email polling (Microsoft Graph API)
- `ingestor/excel_parser.py` — File parsing logic
- `ingestor/db.py` — DB insert, dedup (`is_attachment_processed`, `insert_shipments`, `insert_claim_details`, `update_order_status`, `update_kargo_order_status`)
- `ingestor/requirements.txt` — Python dependencies

### Status
- Running as Docker container `baxter_ingestor`
- Periodic checks via APScheduler
- New emails auto-processed → parsed → inserted → dashboard updates within 5 min refresh

### Microsoft Tenant Setup
- Paul needs to provide email address for ingestion
- Requires Microsoft tenant ID setup for Graph API access
- Jahanzeb knows the tenant setup process

---

## COMPLETE PROJECT HISTORY & CONVERSATION LOG

### Phase 1: Initial Setup (Before March 29, 2026)
- Set up AWS EC2 with Docker, PostgreSQL, Grafana, Python ingestor
- Created dashboards 01, 02, 04
- Email ingestion pipeline working

### Phase 2: Summary Dashboard Creation (March 29, 2026)
- Created `00_summary_dashboard.json` to match Paul's reference image
- **Bug 1:** All panels showed 0 → Fixed: Missing `DS_POSTGRESQL` datasource template variable
- **Bug 2:** Bar chart "No data" → Fixed: Column aliases didn't match override matchers
- **Bug 3:** $ Saved wrong amount → Paul said $28,920 in reference was demo data, real data shows $185K. Initially tried `claim_amount/quantity` formula, Paul called it "zabardasti ki calculation" → Reverted to correct `SUM(ABS(claim_amount))`
- **Bug 4:** Percent changes showed 2000%+ → Cumulative approach was wrong → Fixed to month-over-month comparison (2 data points)
- Added weekly bars instead of daily for time series chart
- All values verified against database

### Phase 3: Paul's Feature Requests (March 30, 2026)

**Request 1: Paul asked about Valid Claim + Order Status columns**
- Paul asked: "Does Valid Claim = No mean all LPNs were read?"
- Answer: NO — Valid Claim = No means we COULDN'T find a matching shipment. Valid Claim = Yes + Order Status = Perfect means all LPNs scanned and order delivered perfectly.

**Request 2: Add detail table below $ Saved**
- Paul wanted a table showing: Customer, Order Number, Shortage $ for each verified claim
- Initially asked for grouped totals, then clarified he wants INDIVIDUAL orders (each on its own row)
- Added "Verified Shortage Details" table panel (id: 8)

**Request 3: Change $ Saved to only Perfect orders**
- Paul explained: Only claims where Order Status = "Perfect" are recoverable money
- "Short" orders can't be disputed (no proof of full delivery)
- Changed ALL relevant panels (3, 4, 7, 8) to add `AND s.order_status = 'Perfect'` to EXISTS clause
- **Before:** 90 claims, $185,716.79
- **After:** 63 claims, $123,904.87

**Request 4: Rename "Valid Claim" to "Order Scanned"**
- Changed in dashboard 04 (Claim Validation Details table)
- SQL alias, field override matchers, and value mappings all updated

### Phase 4: V2 Dashboard & New Data (April 2026)

**V2 VP Summary Dashboard created and deployed:**
- Paul asked for a "dumbed down" summary screen for his VP
- Created `_gen_v2_dashboard.py` generator → produced `05_v2_summary_dashboard.json`
- 13 panels: KPIs, stacked bar, gauge, line chart, monthly table, missed opportunities, key takeaway, bottom line
- UID: `summary-dashboard-v2`, deployed to EC2 Grafana

**New data files loaded (April 15):**
- CS_RMA_DETAIL_Embed_Excel_100073316606.xlsx — 682 new claim rows (14,774 → 15,456 claims, through April 9, 2026)
- 2 Kargo order_level CSVs — 23 orders processed, 19 shipment rows updated with order_status (Perfect/Short)

**Kargo Order Level Parser built:**
- `parse_order_level_csv()` added to `excel_parser.py` — parses Kargo scan CSV files
- `update_kargo_order_status()` added to `db.py` — updates shipments.order_status with RIGHT(N) matching
- Detection added in `detect_and_parse()` for `order_level` filename pattern
- `manual_upload.py` updated to handle `order_level` file type

**Milestone 9 ($450) APPROVED** — Paul approved the V2 dashboard milestone
**Milestone 10 ($450) activated** — Visual review and data validation, due April 25

### Phase 5: Client Discussion (March 30-31 & April 15, 2026)

**Paul's Message about Hosting & Future:**
- Paul wants Jahanzeb to host the system (pending IT approval)
- Data acquisition is "clunky" — Paul wants it API-driven instead of email
- Paul has meetings with AWS team (Wednesday) and Azure team (Friday)
- Microsoft team wants to move away from email ingestion ("shouts college")
- IT has extra PowerBI licenses but Paul prefers Grafana
- Paul will send updated files bi-weekly
- Paul's VP loved the dashboards — "It's not going anywhere"
- Paul asked about closing project or keeping alive — decided to keep alive

**Hosting Decision (Updated April 15):**
- Paul got his own AWS server — but it's Baxter-managed, private network, NO public IP, NO SSH
- Access: internal VPN + RDP only, credentials managed by IT
- Paul CANNOT share SSH keys or provide external access
- Paul working with IT to get Docker approved on the server
- **Plan:** Jahanzeb builds a single deployment script (`setup_baxter.sh`) that Paul's IT team runs — one command sets up everything
- Script is repeatable — can rebuild/reset anytime
- After IT runs script → screen share with Jahanzeb to validate together

**PowerBI vs Grafana Recommendation:**
- Recommended Grafana because: real-time refresh (5 min vs hourly), zero licensing cost, already built and verified, Docker fit, built-in alerting
- PowerBI better for Excel-like modeling and non-technical users, but not ideal for real-time operational monitoring

**Email for Ingestion:**
- Paul needs to provide email address for the ingestor pipeline
- Jahanzeb knows Microsoft tenant ID setup process

---

## FILE STRUCTURE
```
paul-demo-pipeline/
├── .dockerignore
├── .env                        # Environment variables (not in git)
├── .env.example                # Template for .env
├── .gitignore
├── docker-compose.yml          # Docker services config
├── manual_upload.py            # Manual file ingestion (bypass email)
├── project_context.md          # THIS FILE — all project context
├── README.md
├── AZURE_QUICKSTART.md
├── AZURE_SETUP_GUIDE.md
├── docs/
│   ├── AZURE_SETUP_GUIDE.html  # Deployed to EC2 Nginx
│   └── BAXTER_DOCUMENTATION.html
├── grafana/
│   ├── dashboards/
│   │   ├── 00_summary_dashboard.json  # Main summary (V1)
│   │   ├── 01_volume_over_time.json   # Volume trends
│   │   ├── 02_shipment_order_breakdown.json  # Barcode validation
│   │   ├── 04_claim_validation.json   # Detail board
│   │   └── 05_v2_summary_dashboard.json  # VP Summary (V2)
│   └── provisioning/
│       ├── dashboards/dashboard.yaml
│       └── datasources/postgres.yaml
├── ingestor/
│   ├── main.py               # Entry point, scheduler
│   ├── graph_api.py           # Email polling (Microsoft Graph)
│   ├── excel_parser.py        # File parsers (MS_Kargo, Result CSV, AllOrders, CS_RMA, Order Level)
│   ├── db.py                  # Database operations (insert, update, dedup)
│   ├── seed_data.py           # Sample data seeder
│   ├── Dockerfile
│   └── requirements.txt
├── postgres/
│   └── init.sql               # Database schema
└── sample_data/
    ├── CS_RMA_DETAIL_Embed_Excel_100073316606.xlsx  # Latest CS_RMA (loaded April 2026)
    ├── order_level_61599177,...csv                    # Kargo scan data (17 orders)
    └── order_level_61753307,...csv                    # Kargo scan data (6 orders)
```

---

## IMPORTANT LESSONS LEARNED
1. **Never force calculations to match demo data** — Use correct formulas with actual data
2. **PowerShell escaping is a nightmare** — Always use Python scripts to generate/modify JSON, then delete the script
3. **Grafana dashboard JSON editing** — Dashboard JSONs were hand-crafted (not exported from UI), so they need careful manual editing
4. **Docker compose service names ≠ container names** — Use `grafana` not `baxter_grafana` for docker compose commands
5. **Percent changes** — Use 2-point time series (previous period total vs current total), NOT cumulative running totals
6. **Paul verifies everything** — Client cross-checks all numbers manually, so data must be 100% accurate

---

## WHAT TO DO WHEN PAUL SENDS NEW DATA FILES
1. Place files in `sample_data/` or process through ingestor
2. If manual: use `manual_upload.py` or run SQL inserts
3. If via email: ingestor auto-processes
4. After new data: verify dashboard numbers match with SQL queries
5. Paul sends files approximately every 2 weeks

---

## PENDING / FUTURE WORK
1. **Deployment script for Paul's server** — Build `setup_baxter.sh` that Paul's IT team can run (Docker install + full stack setup). Paul waiting on Docker approval from IT.
2. **Milestone 10 validation** — V2 dashboard visual review and data validation with Paul, due April 25
3. **API-driven data acquisition** — Replace email ingestion with direct API pulls (Paul discussing with AWS/Azure teams)
4. **Microsoft Graph API backdoor** — Paul's IT still working on this. Once ready, integrate email attachment capture.
5. **KPI alerts** — Grafana can send alerts on thresholds
6. **Microsoft tenant setup** — For Graph API email access, Paul needs to provide email address

---

**This file is the SINGLE SOURCE OF TRUTH for this project. Any new AI session should read this file FIRST before doing anything.**

**Last Updated:** April 15, 2026
**Last Git Commit:** pending (cleanup + V2 dashboard + order_level parser)

# Baxter Demo Pipeline

**Email → AWS RDS → Grafana** — Automated shipment data ingestion and visualization.

## Architecture

```
Microsoft 365 Outlook
       │  (Graph API / DEMO_MODE)
       ▼
  Python Ingestor
  (every 30 min)
       │  openpyxl parse + dedup hash
       ▼
Amazon RDS PostgreSQL  ←──── ON CONFLICT DO NOTHING
       │
       ▼
  Grafana Dashboards
  (4 dashboards, auto-provisioned)
```

## Quick Start (Local Demo)

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed & running
- Excel sample files in `./sample_data/`

### 1. Copy environment file
```bash
cp .env.example .env
```
> For demo, **no changes needed** — `DEMO_MODE=true` is the default.

### 2. Add sample Excel files
Place the `.xlsx` files into the `./sample_data/` folder:
```
demo-pipeline/
└── sample_data/
    ├── MS_Kargo.xlsx
    └── CS_RMA_DETAIL_Embed_Excel_058073244343.xlsx
```

### 3. Start all services
```bash
docker compose up -d --build
```
Wait ~20 seconds for PostgreSQL to initialize.

### 4. Load seed data (backfill)
```bash
docker exec baxter_ingestor python seed_data.py
```

### 5. Open Grafana
- URL: http://localhost:3000
- Login: `admin` / `admin123`
- All 4 dashboards auto-load on first start.

---

## Dashboards

| # | Name | Description |
|---|------|-------------|
| 1 | Volume Over Time | Hourly/daily shipment counts |
| 2 | Shipment & Order Breakdown | Carrier SCAC distribution + table |
| 3 | Data Quality | Missing PRO_NUMBER gauge + trend |
| 4 | Cost Savings | RMA credit recovery by carrier |

---

## Running a Single Ingestion Cycle

Simulate a new email arriving (for demo recording):
```bash
docker exec baxter_ingestor python main.py --once
```

---

## Reset & Reload Data

```bash
# Clear DB and reload from scratch
docker exec baxter_ingestor python seed_data.py --reset
```

---

## Switching to Production (Real Microsoft 365)

1. Edit `.env`:
```env
DEMO_MODE=false
GRAPH_TENANT_ID=your-tenant-id
GRAPH_CLIENT_ID=your-app-client-id
GRAPH_CLIENT_SECRET=your-app-secret
MAILBOX_EMAIL=your@mailbox.com
```

2. In Azure AD → App registrations, grant:
   - `Mail.Read` (Application permission)
   - `Mail.ReadBasic.All` (Application permission)
   - Admin consent required

3. Restart ingestor:
```bash
docker compose restart ingestor
```

---

## AWS Deployment (EC2)

```bash
# On EC2 instance (Amazon Linux 2)
sudo yum install docker git -y
sudo systemctl start docker
sudo usermod -aG docker ec2-user

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Clone and run
git clone <your-repo>
cd baxter/demo-pipeline
cp .env.example .env
# Edit .env with RDS credentials for POSTGRES_HOST
docker-compose up -d
```

For **Amazon RDS PostgreSQL**, set in `.env`:
```env
POSTGRES_HOST=your-rds-endpoint.rds.amazonaws.com
POSTGRES_PORT=5432
```
> Run `docker compose up -d grafana ingestor` only (skip local postgres service).

---

## Deduplication Strategy

| Level | How |
|-------|-----|
| Attachment | SHA256 hash of file bytes → `processed_attachments` table |
| Row-level | `UNIQUE(sscc18, order_id)` constraint + `ON CONFLICT DO NOTHING` |

---

## Logs

```bash
# View ingestor logs
docker logs -f baxter_ingestor

# View all service logs
docker compose logs -f
```

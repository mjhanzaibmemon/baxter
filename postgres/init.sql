-- ============================================================
-- Baxter Demo Pipeline - PostgreSQL Schema
-- ============================================================

-- Tracks processed email attachments to prevent re-processing
CREATE TABLE IF NOT EXISTS processed_attachments (
    id              SERIAL PRIMARY KEY,
    attachment_hash VARCHAR(64)  UNIQUE NOT NULL,  -- SHA256 of file content
    filename        VARCHAR(255),
    email_id        VARCHAR(255),                  -- Graph API message ID
    processed_at    TIMESTAMPTZ  DEFAULT NOW()
);

-- Main shipments table
CREATE TABLE IF NOT EXISTS shipments (
    id               SERIAL       PRIMARY KEY,
    appointment_date TIMESTAMPTZ  NOT NULL,
    pro_number       VARCHAR(50),                  -- nullable per spec
    sscc18           VARCHAR(30)  NOT NULL,
    scac             VARCHAR(10),
    order_id         VARCHAR(50),
    shipment_id      VARCHAR(50),
    source_file      VARCHAR(255),
    ingested_at      TIMESTAMPTZ  DEFAULT NOW(),
    -- Deduplication: same SSCC18 + ORDER_ID = same shipment
    CONSTRAINT uq_shipment UNIQUE (sscc18, order_id)
);

-- RMA / Credit data (from CS_RMA_DETAIL file)
CREATE TABLE IF NOT EXISTS rma_credits (
    id           SERIAL       PRIMARY KEY,
    carrier_bp   TEXT,
    credit       NUMERIC(15,4),
    count        INTEGER,
    claim_type   VARCHAR(100)  DEFAULT 'Short Shipment',
    source_file  VARCHAR(255),
    ingested_at  TIMESTAMPTZ  DEFAULT NOW(),
    -- Deduplication: same carrier + credit + count = same RMA record
    CONSTRAINT uq_rma_credit UNIQUE (carrier_bp, credit, count)
);

-- -------------------------------------------------------
-- Indexes for fast Grafana time-range queries
-- -------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_shipments_appt_date  ON shipments(appointment_date);
CREATE INDEX IF NOT EXISTS idx_shipments_scac        ON shipments(scac);
CREATE INDEX IF NOT EXISTS idx_shipments_pro_number  ON shipments(pro_number);
CREATE INDEX IF NOT EXISTS idx_shipments_shipment_id ON shipments(shipment_id);
CREATE INDEX IF NOT EXISTS idx_shipments_order_id    ON shipments(order_id);
CREATE INDEX IF NOT EXISTS idx_shipments_ingested_at ON shipments(ingested_at);

-- -------------------------------------------------------
-- Individual claim records (Customer Claim Log in Grafana)
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS claim_details (
    id              SERIAL        PRIMARY KEY,
    claim_date      TIMESTAMPTZ   NOT NULL,
    order_id        VARCHAR(50),
    sscc18          VARCHAR(30),
    claim_amount    NUMERIC(10,2),
    claim_type      VARCHAR(50)   DEFAULT 'Short Shipment',
    carrier_bp      TEXT,
    ingested_at     TIMESTAMPTZ   DEFAULT NOW(),
    -- Deduplication: same date + order + sscc18 + amount = same claim
    CONSTRAINT uq_claim_detail UNIQUE (claim_date, order_id, sscc18, claim_amount)
);
CREATE INDEX IF NOT EXISTS idx_claim_details_date     ON claim_details(claim_date);
CREATE INDEX IF NOT EXISTS idx_claim_details_order_id ON claim_details(order_id);
CREATE INDEX IF NOT EXISTS idx_claim_details_sscc18   ON claim_details(sscc18);

-- -------------------------------------------------------
-- Daily aggregated claim history (Before vs After chart)
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS claim_daily_history (
    id              SERIAL   PRIMARY KEY,
    claim_date      DATE     NOT NULL UNIQUE,
    total_amount    NUMERIC(10,2),
    claim_count     INTEGER,
    moving_avg_7d   NUMERIC(10,2)
);
CREATE INDEX IF NOT EXISTS idx_claim_daily_date ON claim_daily_history(claim_date);

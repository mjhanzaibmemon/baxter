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
    -- Schema v2: additional columns from 35-col CS_RMA_DETAIL Data sheet
    rma_status       VARCHAR(20),
    rma_date         TIMESTAMPTZ,
    doc_type         VARCHAR(10),
    return_doc_type  VARCHAR(10),
    rma_order_number VARCHAR(50),
    po_number        VARCHAR(50),
    order_type       VARCHAR(10),
    reference_number_qualifier VARCHAR(50),
    bol_number       VARCHAR(50),
    original_line_number INTEGER,
    line_number      INTEGER,
    returned_material_status TEXT,
    contact_name     TEXT,
    description      TEXT,
    address_number   VARCHAR(50),
    address_name     TEXT,
    ship_to_number   VARCHAR(50),
    ship_to_name     TEXT,
    item_number      VARCHAR(50),
    unit_of_measure  VARCHAR(20),
    quantity         INTEGER,
    reason_code      VARCHAR(10),
    reason_text      TEXT,
    branch_code      VARCHAR(50),
    branch           TEXT,
    business_unit_code VARCHAR(50),
    business_unit    TEXT,
    serial_number_lot TEXT,
    lot_serial_number TEXT
);
ALTER TABLE claim_details ADD COLUMN IF NOT EXISTS rma_status VARCHAR(20);
ALTER TABLE claim_details ADD COLUMN IF NOT EXISTS rma_date TIMESTAMPTZ;
ALTER TABLE claim_details ADD COLUMN IF NOT EXISTS doc_type VARCHAR(10);
ALTER TABLE claim_details ADD COLUMN IF NOT EXISTS return_doc_type VARCHAR(10);
ALTER TABLE claim_details ADD COLUMN IF NOT EXISTS rma_order_number VARCHAR(50);
ALTER TABLE claim_details ADD COLUMN IF NOT EXISTS po_number VARCHAR(50);
ALTER TABLE claim_details ADD COLUMN IF NOT EXISTS order_type VARCHAR(10);
ALTER TABLE claim_details ADD COLUMN IF NOT EXISTS reference_number_qualifier VARCHAR(50);
ALTER TABLE claim_details ADD COLUMN IF NOT EXISTS bol_number VARCHAR(50);
ALTER TABLE claim_details ADD COLUMN IF NOT EXISTS original_line_number INTEGER;
ALTER TABLE claim_details ADD COLUMN IF NOT EXISTS line_number INTEGER;
ALTER TABLE claim_details ADD COLUMN IF NOT EXISTS returned_material_status TEXT;
ALTER TABLE claim_details ADD COLUMN IF NOT EXISTS contact_name TEXT;
ALTER TABLE claim_details ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE claim_details ADD COLUMN IF NOT EXISTS address_number VARCHAR(50);
ALTER TABLE claim_details ADD COLUMN IF NOT EXISTS address_name TEXT;
ALTER TABLE claim_details ADD COLUMN IF NOT EXISTS ship_to_number VARCHAR(50);
ALTER TABLE claim_details ADD COLUMN IF NOT EXISTS ship_to_name TEXT;
ALTER TABLE claim_details ADD COLUMN IF NOT EXISTS item_number VARCHAR(50);
ALTER TABLE claim_details ADD COLUMN IF NOT EXISTS unit_of_measure VARCHAR(20);
ALTER TABLE claim_details ADD COLUMN IF NOT EXISTS quantity INTEGER;
ALTER TABLE claim_details ADD COLUMN IF NOT EXISTS reason_code VARCHAR(10);
ALTER TABLE claim_details ADD COLUMN IF NOT EXISTS reason_text TEXT;
ALTER TABLE claim_details ADD COLUMN IF NOT EXISTS branch_code VARCHAR(50);
ALTER TABLE claim_details ADD COLUMN IF NOT EXISTS branch TEXT;
ALTER TABLE claim_details ADD COLUMN IF NOT EXISTS business_unit_code VARCHAR(50);
ALTER TABLE claim_details ADD COLUMN IF NOT EXISTS business_unit TEXT;
ALTER TABLE claim_details ADD COLUMN IF NOT EXISTS serial_number_lot TEXT;
ALTER TABLE claim_details ADD COLUMN IF NOT EXISTS lot_serial_number TEXT;
-- Use functional index with COALESCE to handle NULLs (NULL != NULL in SQL UNIQUE)
CREATE UNIQUE INDEX IF NOT EXISTS idx_claim_unique 
    ON claim_details (claim_date, COALESCE(order_id, ''), COALESCE(sscc18, ''), claim_amount);
CREATE INDEX IF NOT EXISTS idx_claim_details_date     ON claim_details(claim_date);
CREATE INDEX IF NOT EXISTS idx_claim_details_order_id ON claim_details(order_id);
CREATE INDEX IF NOT EXISTS idx_claim_details_sscc18   ON claim_details(sscc18);
CREATE INDEX IF NOT EXISTS idx_claim_details_rma_status  ON claim_details(rma_status);
CREATE INDEX IF NOT EXISTS idx_claim_details_doc_type    ON claim_details(doc_type);
CREATE INDEX IF NOT EXISTS idx_claim_details_ship_to     ON claim_details(ship_to_name);
CREATE INDEX IF NOT EXISTS idx_claim_details_item        ON claim_details(item_number);
CREATE INDEX IF NOT EXISTS idx_claim_details_reason_code ON claim_details(reason_code);
CREATE INDEX IF NOT EXISTS idx_claim_details_branch      ON claim_details(branch);

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

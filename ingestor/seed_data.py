"""
seed_data.py — Load sample Excel files + synthetic claim history into DB for demo.

Usage:
    python seed_data.py                     # loads all Excel + claim history
    python seed_data.py --file my_file.xlsx # load specific file
    python seed_data.py --reset             # clear DB and reload everything
"""
import logging
import os
import sys
import random
from datetime import date, timedelta, datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("baxter.seed")

from excel_parser import detect_and_parse
from db import insert_shipments, insert_rma_credits, get_shipment_count
import psycopg2


def get_raw_conn():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        dbname=os.getenv("POSTGRES_DB", "baxter_demo"),
        user=os.getenv("POSTGRES_USER", "baxter"),
        password=os.getenv("POSTGRES_PASSWORD", "baxter_secret_123"),
    )


def reset_db():
    """Clear all tables for a clean demo reload."""
    conn = get_raw_conn()
    with conn.cursor() as cur:
        cur.execute("""
            TRUNCATE shipments, rma_credits, processed_attachments,
                     claim_details, claim_daily_history
            RESTART IDENTITY CASCADE
        """)
    conn.commit()
    conn.close()
    logger.info("Database reset complete — all tables cleared")


def seed_file(filepath: Path):
    """Load a single Excel file into the database."""
    logger.info(f"Seeding: {filepath.name}")
    file_bytes = filepath.read_bytes()
    file_type, rows = detect_and_parse(filepath.name, file_bytes)

    if file_type == "shipments":
        n = insert_shipments(rows, source_file=filepath.name)
        logger.info(f"  ✓ {n} / {len(rows)} shipment rows inserted")
    elif file_type == "rma":
        n = insert_rma_credits(rows, source_file=filepath.name)
        logger.info(f"  ✓ {n} / {len(rows)} RMA credit rows inserted")
    else:
        logger.warning(f"  ✗ Could not parse {filepath.name}")


def seed_claim_history():
    """
    Seed synthetic claim history data showing the 'Before vs After barcode scanning' story.
    - Before May 1, 2024: high claims (~$1800-2400/day) — no barcode validation
    - After  May 1, 2024: low claims  (~$370-500/day)  — barcode scanning implemented
    Result: -79.3% reduction (matching Paul's dashboard mockup)
    """
    random.seed(42)  # fixed seed = reproducible data

    conn = get_raw_conn()
    cur = conn.cursor()

    # Check if already seeded
    cur.execute("SELECT COUNT(*) FROM claim_daily_history")
    if cur.fetchone()[0] > 0:
        logger.info("Claim history already seeded — skipping")
        conn.close()
        return

    # ----------------------------------------------------------------
    # 1. Daily claim history (for Before vs After chart)
    # ----------------------------------------------------------------
    cutover   = date(2024, 5, 1)   # When barcode scanning went live
    start_dt  = date(2024, 3, 15)
    end_dt    = date(2024, 5, 30)

    daily_records = []
    current = start_dt

    while current <= end_dt:
        if current < cutover:
            # BEFORE: high, slowly declining trend  (2400 → ~1200)
            day_num = (current - start_dt).days
            base    = 2400 - day_num * 26 + random.uniform(-250, 250)
            amount  = max(900.0, base)
            count   = random.randint(6, 14)
        else:
            # AFTER: low, stabilising at ~370/day
            day_num = (current - cutover).days
            base    = 520 - day_num * 4.5 + random.uniform(-80, 80)
            amount  = max(200.0, base)
            count   = random.randint(1, 4)

        daily_records.append([current, round(amount, 2), count])
        current += timedelta(days=1)

    # Calculate 7-day moving average
    final_daily = []
    for i, (dt, amt, cnt) in enumerate(daily_records):
        window = [daily_records[j][1] for j in range(max(0, i - 6), i + 1)]
        avg = sum(window) / len(window)
        final_daily.append((dt, amt, cnt, round(avg, 2)))

    cur.executemany(
        """INSERT INTO claim_daily_history (claim_date, total_amount, claim_count, moving_avg_7d)
           VALUES (%s, %s, %s, %s)
           ON CONFLICT (claim_date) DO NOTHING""",
        final_daily,
    )
    logger.info(f"  ✓ {len(final_daily)} daily claim history rows inserted")

    # ----------------------------------------------------------------
    # 2. Individual claim details (Customer Claim Log table)
    # ----------------------------------------------------------------
    order_ids = [
        "OK12345", "PD39911", "IC12455", "OO56779", "QS56788",
        "MN23456", "TR78901", "BV34521", "KL90234", "WX12678",
        "HY45632", "LP09871", "ZR23401", "FQ78234", "AB19023",
    ]
    # Real SSCC18 barcode format (18-20 digit)
    sscc18_pool = [
        "00100854128240235737", "00100854128240235730", "00100854128240235731",
        "00100854128240235732", "00100854128240235733", "00100854128240235734",
        "00100854128240235738", "00100854128240235739", "00345678901234567890",
        "00345678901234567891", "00345678901234567892",
    ]
    carriers = ["UPS", "FedEx", "HSNC", "HSND", "U1DA", "FDX9"]
    claim_types_weighted = (
        ["Short Shipment"] * 7 + ["Damaged"] * 2 + ["Lost Package"] * 1
    )

    claim_rows = []
    for dt, daily_amt, cnt, _ in final_daily:
        for _ in range(cnt):
            claim_dt = datetime(
                dt.year, dt.month, dt.day,
                random.randint(7, 18), random.randint(0, 59), random.randint(0, 59),
            )
            order   = random.choice(order_ids)
            sscc    = random.choice(sscc18_pool)
            amt     = round(random.uniform(180, min(daily_amt * 0.6, 850)), 2)
            ctype   = random.choice(claim_types_weighted)
            carrier = random.choice(carriers)
            claim_rows.append((claim_dt, order, sscc, amt, ctype, carrier))

    cur.executemany(
        """INSERT INTO claim_details
               (claim_date, order_id, sscc18, claim_amount, claim_type, carrier_bp)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        claim_rows,
    )
    logger.info(f"  ✓ {len(claim_rows)} individual claim detail rows inserted")

    conn.commit()
    conn.close()

    # Log the before/after summary
    before_avg = sum(r[1] for r in final_daily if r[0] < cutover) / sum(1 for r in final_daily if r[0] < cutover)
    after_avg  = sum(r[1] for r in final_daily if r[0] >= cutover) / sum(1 for r in final_daily if r[0] >= cutover)
    reduction  = (before_avg - after_avg) / before_avg * 100
    logger.info(f"  📊 Before avg: ${before_avg:,.0f}/day  →  After avg: ${after_avg:,.0f}/day  ({reduction:.1f}% reduction)")


def main():
    do_reset     = "--reset" in sys.argv
    specific_file = None
    for i, arg in enumerate(sys.argv):
        if arg == "--file" and i + 1 < len(sys.argv):
            specific_file = sys.argv[i + 1]

    if do_reset:
        reset_db()

    # ── Seed Excel files ──────────────────────────────────────────────
    excel_dir = Path(os.getenv("DEMO_EXCEL_DIR", "/app/sample_data"))

    if specific_file:
        seed_file(Path(specific_file))
    else:
        files = sorted(excel_dir.glob("*.xlsx"))
        if not files:
            logger.warning(f"No .xlsx files found in {excel_dir}")
        else:
            for f in files:
                seed_file(f)

    # ── Seed synthetic claim history ──────────────────────────────────
    seed_claim_history()

    total = get_shipment_count()
    logger.info(f"Seed complete — Total shipments in DB: {total}")


if __name__ == "__main__":
    main()

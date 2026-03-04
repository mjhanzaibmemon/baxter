"""
db.py — PostgreSQL connection pool and all database operations.
"""
import hashlib
import logging
import os
import psycopg2
import psycopg2.extras
import psycopg2.pool
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# --- Connection Pool (reuses connections instead of open/close each time) ---
_pool = None

def _get_pool():
    """Lazy-init a threaded connection pool."""
    global _pool
    if _pool is None or _pool.closed:
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=5,
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", 5432)),
            dbname=os.getenv("POSTGRES_DB", "baxter_demo"),
            user=os.getenv("POSTGRES_USER", "baxter"),
            password=os.getenv("POSTGRES_PASSWORD", "baxter_secret_123"),
        )
        logger.info("Database connection pool initialized")
    return _pool


def get_connection():
    """Get a connection from the pool."""
    return _get_pool().getconn()


def release_connection(conn):
    """Return a connection back to the pool."""
    try:
        _get_pool().putconn(conn)
    except Exception:
        pass


def is_attachment_processed(file_bytes: bytes) -> bool:
    """Return True if this file content hash has already been processed."""
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM processed_attachments WHERE attachment_hash = %s",
                (file_hash,)
            )
            return cur.fetchone() is not None
    finally:
        release_connection(conn)


def mark_attachment_processed(file_bytes: bytes, filename: str, email_id: str = None):
    """Record an attachment hash as processed to prevent re-ingestion."""
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO processed_attachments (attachment_hash, filename, email_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (attachment_hash) DO NOTHING
                """,
                (file_hash, filename, email_id)
            )
        conn.commit()
        logger.info(f"Marked attachment as processed: {filename} [{file_hash[:12]}...]")
    finally:
        release_connection(conn)


def insert_shipments(rows: list[dict], source_file: str) -> int:
    """
    Bulk-insert shipment rows using execute_values (10-50x faster).
    Uses ON CONFLICT DO NOTHING for deduplication.
    Returns the number of rows actually inserted.
    """
    if not rows:
        return 0

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Prepare tuples for bulk insert
            values = [
                (
                    row.get("appointment_date"),
                    row.get("pro_number"),
                    row.get("sscc18"),
                    row.get("scac"),
                    row.get("order_id"),
                    row.get("shipment_id"),
                    source_file,
                )
                for row in rows
            ]
            count_before = _count_table(cur, "shipments")
            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO shipments
                    (appointment_date, pro_number, sscc18, scac, order_id, shipment_id, source_file)
                VALUES %s
                ON CONFLICT (sscc18, order_id) DO NOTHING
                """,
                values,
                page_size=1000,
            )
            count_after = _count_table(cur, "shipments")
            inserted = count_after - count_before
        conn.commit()
        logger.info(f"Bulk inserted {inserted}/{len(rows)} rows from '{source_file}' (duplicates skipped)")
        return inserted
    except Exception as e:
        conn.rollback()
        logger.error(f"DB insert error: {e}")
        raise
    finally:
        release_connection(conn)


def _count_table(cur, table: str) -> int:
    """Quick row count for a table (used to calculate inserted rows after bulk ON CONFLICT)."""
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    return cur.fetchone()[0]


def insert_rma_credits(rows: list[dict], source_file: str) -> int:
    """Bulk-insert RMA credit rows using execute_values. Uses ON CONFLICT for dedup."""
    if not rows:
        return 0

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            values = [
                (
                    row.get("carrier_bp"),
                    row.get("credit"),
                    row.get("count"),
                    row.get("claim_type", "Short Shipment"),
                    source_file,
                )
                for row in rows
            ]
            count_before = _count_table(cur, "rma_credits")
            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO rma_credits (carrier_bp, credit, count, claim_type, source_file)
                VALUES %s
                ON CONFLICT (carrier_bp, credit, count) DO NOTHING
                """,
                values,
                page_size=500,
            )
            count_after = _count_table(cur, "rma_credits")
            inserted = count_after - count_before
        conn.commit()
        logger.info(f"Bulk inserted {inserted}/{len(rows)} RMA credit rows from '{source_file}' (duplicates skipped)")
        return inserted
    except Exception as e:
        conn.rollback()
        logger.error(f"RMA DB insert error: {e}")
        raise
    finally:
        release_connection(conn)


def get_shipment_count() -> int:
    """Return total shipment rows in DB (for logging/verification)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM shipments")
            return cur.fetchone()[0]
    finally:
        release_connection(conn)


def insert_claim_details(rows: list[dict], source_file: str) -> int:
    """
    Bulk-insert claim detail rows using execute_values (10-50x faster).
    Uses ON CONFLICT for dedup. Returns number of rows inserted.
    """
    if not rows:
        return 0

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            values = [
                (
                    row.get("claim_date"),
                    row.get("order_id"),
                    row.get("sscc18"),
                    row.get("claim_amount"),
                    row.get("claim_type"),
                    row.get("carrier_bp"),
                )
                for row in rows
            ]
            count_before = _count_table(cur, "claim_details")
            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO claim_details
                    (claim_date, order_id, sscc18, claim_amount, claim_type, carrier_bp)
                VALUES %s
                ON CONFLICT (claim_date, order_id, sscc18, claim_amount) DO NOTHING
                """,
                values,
                page_size=1000,
            )
            count_after = _count_table(cur, "claim_details")
            inserted = count_after - count_before
        conn.commit()
        logger.info(f"Bulk inserted {inserted}/{len(rows)} claim detail rows from '{source_file}' (duplicates skipped)")
        return inserted
    except Exception as e:
        conn.rollback()
        logger.error(f"Claim details DB insert error: {e}")
        raise
    finally:
        release_connection(conn)


def rebuild_daily_history():
    """
    Rebuild the claim_daily_history table from claim_details.
    Aggregates daily totals and computes 7-day moving average.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE claim_daily_history")
            cur.execute(
                """
                INSERT INTO claim_daily_history (claim_date, total_amount, claim_count, moving_avg_7d)
                SELECT
                    claim_day,
                    daily_total,
                    daily_count,
                    AVG(daily_total) OVER (
                        ORDER BY claim_day
                        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
                    ) AS moving_avg_7d
                FROM (
                    SELECT
                        DATE(claim_date) AS claim_day,
                        ABS(SUM(claim_amount)) AS daily_total,
                        COUNT(*) AS daily_count
                    FROM claim_details
                    GROUP BY DATE(claim_date)
                ) daily
                ORDER BY claim_day
                """
            )
            inserted = cur.rowcount
        conn.commit()
        logger.info(f"Rebuilt claim_daily_history: {inserted} daily rows")
        return inserted
    except Exception as e:
        conn.rollback()
        logger.error(f"Daily history rebuild error: {e}")
        raise
    finally:
        release_connection(conn)

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


def _shipment_key(row: dict) -> tuple:
    return (row.get("sscc18") or "", row.get("order_id") or "")


def _rma_credit_key(row: dict) -> tuple:
    return (
        row.get("carrier_bp") or "",
        row.get("credit"),
        row.get("count"),
    )


def insert_shipments(rows: list[dict], source_file: str, return_stats: bool = False):
    """
    Bulk-insert shipment rows using execute_values (10-50x faster).
    Uses ON CONFLICT DO NOTHING for deduplication.
    Returns the number of rows actually inserted.
    """
    if not rows:
        stats = {
            "parsed_rows": 0,
            "unique_rows": 0,
            "inserted_rows": 0,
            "duplicate_rows": 0,
            "duplicate_rows_in_file": 0,
            "duplicate_rows_existing": 0,
        }
        return stats if return_stats else 0

    unique_rows = len({_shipment_key(row) for row in rows})
    duplicate_rows_in_file = len(rows) - unique_rows

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
        duplicate_rows_existing = max(unique_rows - inserted, 0)
        stats = {
            "parsed_rows": len(rows),
            "unique_rows": unique_rows,
            "inserted_rows": inserted,
            "duplicate_rows": len(rows) - inserted,
            "duplicate_rows_in_file": duplicate_rows_in_file,
            "duplicate_rows_existing": duplicate_rows_existing,
        }
        logger.info(
            f"Bulk inserted {inserted}/{len(rows)} rows from '{source_file}' "
            f"(duplicates skipped: total={stats['duplicate_rows']}, "
            f"in_file={duplicate_rows_in_file}, existing={duplicate_rows_existing})"
        )
        return stats if return_stats else inserted
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


def insert_rma_credits(rows: list[dict], source_file: str, return_stats: bool = False):
    """Bulk-insert RMA credit rows using execute_values. Uses ON CONFLICT for dedup."""
    if not rows:
        stats = {
            "parsed_rows": 0,
            "unique_rows": 0,
            "inserted_rows": 0,
            "duplicate_rows": 0,
            "duplicate_rows_in_file": 0,
            "duplicate_rows_existing": 0,
        }
        return stats if return_stats else 0

    unique_rows = len({_rma_credit_key(row) for row in rows})
    duplicate_rows_in_file = len(rows) - unique_rows

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
        duplicate_rows_existing = max(unique_rows - inserted, 0)
        stats = {
            "parsed_rows": len(rows),
            "unique_rows": unique_rows,
            "inserted_rows": inserted,
            "duplicate_rows": len(rows) - inserted,
            "duplicate_rows_in_file": duplicate_rows_in_file,
            "duplicate_rows_existing": duplicate_rows_existing,
        }
        logger.info(
            f"Bulk inserted {inserted}/{len(rows)} RMA credit rows from '{source_file}' "
            f"(duplicates skipped: total={stats['duplicate_rows']}, "
            f"in_file={duplicate_rows_in_file}, existing={duplicate_rows_existing})"
        )
        return stats if return_stats else inserted
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


def update_order_status(rows: list[dict]) -> dict:
    """
    Update shipments.order_status from AllOrders.csv data.
    Matches on order_id = order_number.
    Returns stats dict with matched/unmatched counts.
    """
    if not rows:
        return {"total": 0, "updated": 0, "not_found": 0}

    conn = get_connection()
    try:
        updated = 0
        not_found = 0
        with conn.cursor() as cur:
            for row in rows:
                cur.execute(
                    "UPDATE shipments SET order_status = %s WHERE order_id = %s",
                    (row["order_status"], row["order_number"]),
                )
                if cur.rowcount > 0:
                    updated += cur.rowcount
                else:
                    not_found += 1
        conn.commit()
        stats = {"total": len(rows), "updated": updated, "not_found": not_found}
        logger.info(
            f"Order status update: {updated} shipment rows updated, "
            f"{not_found} order_numbers not found in shipments"
        )
        return stats
    except Exception as e:
        conn.rollback()
        logger.error(f"Order status update error: {e}")
        raise
    finally:
        release_connection(conn)


def update_kargo_order_status(rows: list[dict]) -> dict:
    """
    Update shipments.order_status from Kargo order_level CSV data.
    Matches on RIGHT(order_id, 8) = original_order since Kargo order numbers
    have an 8-digit shipment prefix stripped.
    Returns stats dict with matched/unmatched counts.
    """
    if not rows:
        return {"total": 0, "updated": 0, "not_found": 0}

    conn = get_connection()
    try:
        updated = 0
        not_found = 0
        with conn.cursor() as cur:
            for row in rows:
                # Try exact match first, then RIGHT(8) fallback
                cur.execute(
                    "UPDATE shipments SET order_status = %s WHERE order_id = %s",
                    (row["order_status"], row["order_number"]),
                )
                if cur.rowcount == 0:
                    # Fallback: match on last 8 digits of order_id
                    cur.execute(
                        "UPDATE shipments SET order_status = %s WHERE RIGHT(order_id, %s) = %s",
                        (row["order_status"], len(row["order_number"]), row["order_number"]),
                    )
                if cur.rowcount > 0:
                    updated += cur.rowcount
                else:
                    not_found += 1
        conn.commit()
        stats = {"total": len(rows), "updated": updated, "not_found": not_found}
        logger.info(
            f"Kargo order status update: {updated} shipment rows updated, "
            f"{not_found} order_numbers not found in shipments"
        )
        return stats
    except Exception as e:
        conn.rollback()
        logger.error(f"Kargo order status update error: {e}")
        raise
    finally:
        release_connection(conn)


def insert_claim_details(rows: list[dict], source_file: str, return_stats: bool = False):
    """
    Bulk-insert claim detail rows using execute_values (10-50x faster).
    Uses ON CONFLICT for dedup. Returns number of rows inserted.
    """
    if not rows:
        stats = {
            "parsed_rows": 0,
            "unique_rows": 0,
            "inserted_rows": 0,
            "updated_rows": 0,
            "duplicate_rows_in_file": 0,
        }
        return stats if return_stats else 0

    # Deduplicate rows by unique key BEFORE inserting to avoid
    # "ON CONFLICT DO UPDATE cannot affect row a second time" error.
    # Keep last occurrence (most complete data).
    deduped = {}
    for row in rows:
        key = (
            row.get("claim_date"),
            row.get("order_id") or "",
            row.get("sscc18") or "",
            row.get("claim_amount"),
        )
        deduped[key] = row
    unique_rows = list(deduped.values())
    duplicate_rows_in_file = len(rows) - len(unique_rows)
    logger.info(
        f"Deduped {len(rows)} → {len(unique_rows)} unique claim rows "
        f"(duplicates inside file: {duplicate_rows_in_file})"
    )

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
                    # Schema v2 fields
                    row.get("rma_status"),
                    row.get("rma_date"),
                    row.get("doc_type"),
                    row.get("return_doc_type"),
                    row.get("rma_order_number"),
                    row.get("po_number"),
                    row.get("order_type"),
                    row.get("reference_number_qualifier"),
                    row.get("bol_number"),
                    row.get("original_line_number"),
                    row.get("line_number"),
                    row.get("returned_material_status"),
                    row.get("contact_name"),
                    row.get("description"),
                    row.get("address_number"),
                    row.get("address_name"),
                    row.get("ship_to_number"),
                    row.get("ship_to_name"),
                    row.get("item_number"),
                    row.get("unit_of_measure"),
                    row.get("quantity"),
                    row.get("reason_code"),
                    row.get("reason_text"),
                    row.get("branch_code"),
                    row.get("branch"),
                    row.get("business_unit_code"),
                    row.get("business_unit"),
                    row.get("serial_number_lot"),
                    row.get("lot_serial_number"),
                )
                for row in unique_rows
            ]
            count_before = _count_table(cur, "claim_details")
            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO claim_details
                    (claim_date, order_id, sscc18, claim_amount, claim_type, carrier_bp,
                     rma_status, rma_date, doc_type, return_doc_type, rma_order_number, po_number,
                     order_type, reference_number_qualifier, bol_number, original_line_number,
                     line_number, returned_material_status, contact_name, description,
                     address_number, address_name, ship_to_number, ship_to_name,
                     item_number, unit_of_measure, quantity, reason_code, reason_text,
                     branch_code, branch, business_unit_code, business_unit,
                     serial_number_lot, lot_serial_number)
                VALUES %s
                ON CONFLICT (claim_date, COALESCE(order_id, ''), COALESCE(sscc18, ''), claim_amount)
                DO UPDATE SET
                    rma_status       = COALESCE(EXCLUDED.rma_status, claim_details.rma_status),
                    rma_date         = COALESCE(EXCLUDED.rma_date, claim_details.rma_date),
                    doc_type         = COALESCE(EXCLUDED.doc_type, claim_details.doc_type),
                    return_doc_type  = COALESCE(EXCLUDED.return_doc_type, claim_details.return_doc_type),
                    rma_order_number = COALESCE(EXCLUDED.rma_order_number, claim_details.rma_order_number),
                    po_number        = COALESCE(EXCLUDED.po_number, claim_details.po_number),
                    order_type       = COALESCE(EXCLUDED.order_type, claim_details.order_type),
                    reference_number_qualifier = COALESCE(EXCLUDED.reference_number_qualifier, claim_details.reference_number_qualifier),
                    bol_number       = COALESCE(EXCLUDED.bol_number, claim_details.bol_number),
                    original_line_number = COALESCE(EXCLUDED.original_line_number, claim_details.original_line_number),
                    line_number      = COALESCE(EXCLUDED.line_number, claim_details.line_number),
                    returned_material_status = COALESCE(EXCLUDED.returned_material_status, claim_details.returned_material_status),
                    contact_name     = COALESCE(EXCLUDED.contact_name, claim_details.contact_name),
                    description      = COALESCE(EXCLUDED.description, claim_details.description),
                    address_number   = COALESCE(EXCLUDED.address_number, claim_details.address_number),
                    address_name     = COALESCE(EXCLUDED.address_name, claim_details.address_name),
                    ship_to_number   = COALESCE(EXCLUDED.ship_to_number, claim_details.ship_to_number),
                    ship_to_name     = COALESCE(EXCLUDED.ship_to_name, claim_details.ship_to_name),
                    item_number      = COALESCE(EXCLUDED.item_number, claim_details.item_number),
                    unit_of_measure  = COALESCE(EXCLUDED.unit_of_measure, claim_details.unit_of_measure),
                    quantity         = COALESCE(EXCLUDED.quantity, claim_details.quantity),
                    reason_code      = COALESCE(EXCLUDED.reason_code, claim_details.reason_code),
                    reason_text      = COALESCE(EXCLUDED.reason_text, claim_details.reason_text),
                    branch_code      = COALESCE(EXCLUDED.branch_code, claim_details.branch_code),
                    branch           = COALESCE(EXCLUDED.branch, claim_details.branch),
                    business_unit_code = COALESCE(EXCLUDED.business_unit_code, claim_details.business_unit_code),
                    business_unit    = COALESCE(EXCLUDED.business_unit, claim_details.business_unit),
                    serial_number_lot = COALESCE(EXCLUDED.serial_number_lot, claim_details.serial_number_lot),
                    lot_serial_number = COALESCE(EXCLUDED.lot_serial_number, claim_details.lot_serial_number)
                """,
                values,
                page_size=1000,
            )
            count_after = _count_table(cur, "claim_details")
            inserted = count_after - count_before
        conn.commit()
        updated = max(len(unique_rows) - inserted, 0)
        stats = {
            "parsed_rows": len(rows),
            "unique_rows": len(unique_rows),
            "inserted_rows": inserted,
            "updated_rows": updated,
            "duplicate_rows_in_file": duplicate_rows_in_file,
        }
        logger.info(
            f"Bulk upserted {len(rows)} claim detail rows from '{source_file}' "
            f"({inserted} new, {updated} updated, {duplicate_rows_in_file} duplicate rows inside file)"
        )
        return stats if return_stats else inserted
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
                        SUM(ABS(claim_amount)) AS daily_total,
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

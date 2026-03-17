"""
main.py — Entry point for the Baxter email ingestion service.

Uses APScheduler for reliable cron-style scheduling with:
  - Missed job recovery (coalescing)
  - Graceful shutdown
  - Error isolation (failed jobs don't crash the scheduler)

Can also be run once with: python main.py --once
"""
import logging
import os
import sys
import signal
from dotenv import load_dotenv

load_dotenv()

# ---- Logging Setup ----
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("baxter.main")

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from graph_api import poll_mailbox, send_email_alert
from excel_parser import detect_and_parse
from db import (
    is_attachment_processed,
    mark_attachment_processed,
    insert_shipments,
    insert_rma_credits,
    insert_claim_details,
    rebuild_daily_history,
    get_shipment_count,
)


def _build_success_email_body(filename: str, file_type: str, total_inserted: int, detail_lines: list[str]) -> str:
    return f"""File: {filename}
File Type: {file_type.upper()}
Total Rows Inserted: {total_inserted}

Details:
{chr(10).join('  - ' + line for line in detail_lines)}

Dashboard: http://localhost:3000
Status: ✅ Ready for viewing"""


def run_ingestion_cycle():
    """One full ingestion cycle: poll → parse → deduplicate → insert."""
    logger.info("=" * 60)
    logger.info("Starting ingestion cycle")

    try:
        attachments = poll_mailbox()
    except Exception as e:
        logger.error(f"Failed to poll mailbox: {e}")
        return

    if not attachments:
        logger.info("No new attachments found — nothing to process")
        return

    total_inserted = 0
    total_skipped  = 0

    for filename, file_bytes, email_id in attachments:
        logger.info(f"Processing: {filename}")

        # --- Attachment-level deduplication ---
        if is_attachment_processed(file_bytes):
            logger.info(f"  ↳ Already processed — skipping {filename}")
            total_skipped += 1
            
            # Send notification for duplicate file
            send_email_alert(
                subject=f"Duplicate File Skipped: {filename}",
                body=f"""File: {filename}
Status: ⚠️ Duplicate Detected

Reason: This file has already been processed previously.

The system detected that this exact file (same content hash) was already 
imported into the database. To prevent duplicate data entry, the file 
was skipped.

If you believe this is an error, please verify:
1. File content is actually new/different
2. Previous processing was incomplete
3. Database deduplication is working correctly

Dashboard: http://localhost:3000
Total files skipped in this cycle: {total_skipped}""",
                is_success=False  # Warning, not error
            )
            continue

        # --- Parse ---
        try:
            file_type, rows, claim_rows = detect_and_parse(filename, file_bytes)
        except Exception as e:
            logger.error(f"  ↳ Parse error for {filename}: {e}")
            # Send error alert
            send_email_alert(
                subject=f"File Processing Failed: {filename}",
                body=f"""File: {filename}
Error Type: Parse Error
Error Message: {str(e)}

Please check the file format and try again.""",
                is_success=False
            )
            continue

        if file_type == "unknown" or (not rows and not claim_rows):
            logger.warning(f"  ↳ No parseable data in {filename}")
            continue

        # --- Insert to DB ---
        try:
            n = 0
            details = []
            if file_type == "shipments":
                shipment_stats = insert_shipments(rows, source_file=filename, return_stats=True)
                n = shipment_stats["inserted_rows"]
                details.extend([
                    f"Shipments parsed: {shipment_stats['parsed_rows']}",
                    f"New shipments inserted: {shipment_stats['inserted_rows']}",
                    f"Duplicate shipments skipped: {shipment_stats['duplicate_rows']}",
                    f"Duplicate shipments already in DB: {shipment_stats['duplicate_rows_existing']}",
                    f"Duplicate shipments inside file: {shipment_stats['duplicate_rows_in_file']}",
                ])
            elif file_type == "rma":
                rma_stats = None
                claim_stats = None
                daily_history_rows = 0
                if rows:
                    rma_stats = insert_rma_credits(rows, source_file=filename, return_stats=True)
                    n += rma_stats["inserted_rows"]
                if claim_rows:
                    claim_stats = insert_claim_details(claim_rows, source_file=filename, return_stats=True)
                    logger.info(
                        f"  ↳ Claim details processed: {claim_stats['parsed_rows']} parsed, "
                        f"{claim_stats['inserted_rows']} inserted, {claim_stats['updated_rows']} updated"
                    )
                    daily_history_rows = rebuild_daily_history()
                    n += claim_stats["inserted_rows"]

                if rma_stats:
                    details.extend([
                        f"RMA credits parsed: {rma_stats['parsed_rows']}",
                        f"New RMA credits inserted: {rma_stats['inserted_rows']}",
                        f"Duplicate RMA credits skipped: {rma_stats['duplicate_rows']}",
                        f"Duplicate RMA credits already in DB: {rma_stats['duplicate_rows_existing']}",
                        f"Duplicate RMA credits inside file: {rma_stats['duplicate_rows_in_file']}",
                    ])
                if claim_stats:
                    details.extend([
                        f"Claim details parsed: {claim_stats['parsed_rows']}",
                        f"Unique claim details after file dedup: {claim_stats['unique_rows']}",
                        f"New claim details inserted: {claim_stats['inserted_rows']}",
                        f"Existing claim details updated: {claim_stats['updated_rows']}",
                        f"Duplicate claim rows inside file: {claim_stats['duplicate_rows_in_file']}",
                        f"Daily history rows rebuilt: {daily_history_rows}",
                    ])

            total_inserted += n

            # Mark as processed ONLY after successful insert
            mark_attachment_processed(file_bytes, filename, email_id)
            logger.info(f"  ↳ Done: {n} rows inserted from {filename}")
            
            # Send success alert
            if not details:
                details.append("No supported rows were inserted")

            send_email_alert(
                subject=f"File Processed Successfully: {filename}",
                body=_build_success_email_body(filename, file_type, n, details),
                is_success=True
            )

        except Exception as e:
            logger.error(f"  ↳ DB error for {filename}: {e}")
            # Send error alert
            send_email_alert(
                subject=f"Database Error: {filename}",
                body=f"""File: {filename}
Error Type: Database Error
Error Message: {str(e)}

The file was parsed successfully but failed to insert into the database.
Please check database logs for more details.""",
                is_success=False
            )
            continue

    total_in_db = get_shipment_count()
    logger.info(
        f"Cycle complete — Inserted: {total_inserted} | Skipped: {total_skipped} | "
        f"Total shipments in DB: {total_in_db}"
    )
    logger.info("=" * 60)


def main():
    run_once = "--once" in sys.argv
    interval = int(os.getenv("POLL_INTERVAL_MINUTES", 30))

    logger.info("Baxter Email Ingestion Service starting")
    logger.info(f"  Mode: {'DEMO' if os.getenv('DEMO_MODE','true').lower()=='true' else 'PRODUCTION'}")
    logger.info(f"  Poll interval: {interval} minutes")

    if run_once:
        logger.info("Running single cycle (--once flag)")
        run_ingestion_cycle()
        return

    # --- APScheduler: reliable interval scheduling ---
    scheduler = BlockingScheduler(
        job_defaults={
            "coalesce": True,          # If missed, run once (not N times)
            "max_instances": 1,        # Only 1 cycle at a time
            "misfire_grace_time": 300,  # 5 min grace for misfired jobs
        }
    )

    # Graceful shutdown on SIGTERM/SIGINT
    def shutdown(signum, frame):
        logger.info("Shutdown signal received — stopping scheduler...")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    # Run first cycle immediately
    logger.info("Running initial ingestion cycle...")
    run_ingestion_cycle()

    # Schedule recurring job starting from next interval
    from datetime import datetime, timedelta
    next_run = datetime.now() + timedelta(minutes=interval)
    
    scheduler.add_job(
        run_ingestion_cycle,
        trigger=IntervalTrigger(minutes=interval),
        id="email_ingestion",
        name="Email Ingestion Cycle",
        next_run_time=next_run,  # Schedule first recurring run
    )

    # Start scheduler loop
    logger.info(f"Scheduler started — polling every {interval} minutes")
    logger.info(f"Next scheduled run: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")


if __name__ == "__main__":
    main()

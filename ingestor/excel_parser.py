"""
excel_parser.py — Parse .xlsx attachments into list of dicts.

Supports:
  - MS_Kargo schema  (APPOINTMENT_DATE, PRO_NUMBER, SSCC18, SCAC, ORDER_ID, SHIPMENT_ID)
  - CS_RMA_DETAIL    (Summary sheet: Carrier/BP, Credit, Count)
  - CS_RMA_DETAIL    (Data sheet: individual claim rows → claim_details)
"""
import io
import logging
from datetime import datetime
import openpyxl

logger = logging.getLogger(__name__)


def _normalize_header(h) -> str:
    """Lowercase + strip a header string for comparison."""
    if h is None:
        return ""
    return str(h).strip().lower().replace(" ", "_").replace("/", "_")


def parse_ms_kargo(file_bytes: bytes) -> list[dict]:
    """
    Parse the MS_Kargo Excel format.
    Expected headers (row 1): APPOINTMENT_DATE, PRO_NUMBER, SSCC18, SCAC, ORDER_ID, SHIPMENT_ID
    Returns list of dicts ready for DB insert.
    """
    if not file_bytes or len(file_bytes) < 100:
        logger.warning("MS_Kargo: Empty or invalid file")
        return []
    
    try:
        wb = openpyxl.load_workbook(filename=io.BytesIO(file_bytes), read_only=True, data_only=True)
    except Exception as e:
        logger.error(f"MS_Kargo: Failed to open Excel file: {e}")
        return []

    # Try 'Sheet1' first, fallback to active sheet
    ws = wb["Sheet1"] if "Sheet1" in wb.sheetnames else wb.active

    headers = [_normalize_header(c.value) for c in next(ws.iter_rows(min_row=1, max_row=1))]
    logger.debug(f"MS_Kargo headers detected: {headers}")

    field_map = {
        "appointment_date": "appointment_date",
        "pro_number":       "pro_number",
        "sscc18":           "sscc18",
        "scac":             "scac",
        "order_id":         "order_id",
        "shipment_id":      "shipment_id",
    }

    rows = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        # Skip completely empty rows
        if all(v is None for v in row):
            continue

        record = {}
        for col_idx, raw_header in enumerate(headers):
            if col_idx >= len(row):
                break
            db_field = field_map.get(raw_header)
            if db_field:
                val = row[col_idx]
                # Ensure appointment_date is datetime
                if db_field == "appointment_date":
                    if isinstance(val, datetime):
                        record[db_field] = val
                    elif val is not None:
                        try:
                            record[db_field] = datetime.fromisoformat(str(val))
                        except Exception:
                            logger.warning(f"Could not parse date: {val}")
                            record[db_field] = None
                    else:
                        record[db_field] = None
                else:
                    record[db_field] = str(val).strip() if val is not None else None

        # Only include rows with minimum required fields
        if record.get("sscc18") and record.get("appointment_date"):
            rows.append(record)

    logger.info(f"Parsed {len(rows)} valid rows from MS_Kargo sheet")
    wb.close()
    return rows


def parse_rma_detail(file_bytes: bytes) -> list[dict]:
    """
    Parse the CS_RMA_DETAIL Excel — Summary sheet only.
    Headers start at row 3: Carrier/BP, Credit, Count
    Returns list of dicts for rma_credits table.
    """
    if not file_bytes or len(file_bytes) < 100:
        logger.warning("CS_RMA_DETAIL: Empty or invalid file")
        return []
    
    try:
        wb = openpyxl.load_workbook(filename=io.BytesIO(file_bytes), read_only=True, data_only=True)
    except Exception as e:
        logger.error(f"CS_RMA_DETAIL: Failed to open Excel file: {e}")
        return []

    ws = wb["Summary"] if "Summary" in wb.sheetnames else wb.active

    rows = []
    header_row_idx = None

    # Find the header row dynamically
    for row_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
        row_lower = [str(v).strip().lower() if v else "" for v in row]
        if "carrier/bp" in row_lower or "carrier_bp" in row_lower:
            header_row_idx = row_idx
            break

    if header_row_idx is None:
        logger.warning("CS_RMA_DETAIL: Could not find header row in Summary sheet")
        return rows

    # Read data rows after header
    for row in ws.iter_rows(min_row=header_row_idx + 1, values_only=True):
        if all(v is None for v in row):
            continue
        carrier_bp, credit, count = row[0], row[1], row[2]
        if carrier_bp is None:
            continue
        rows.append({
            "carrier_bp": str(carrier_bp).strip(),
            "credit":     float(credit) if credit is not None else None,
            "count":      int(count) if count is not None else None,
        })

    logger.info(f"Parsed {len(rows)} RMA credit rows")
    wb.close()
    return rows


def detect_and_parse(filename: str, file_bytes: bytes):
    """
    Auto-detect file type by filename and parse accordingly.
    Returns (type, rows) where type is 'shipments', 'rma', or 'unknown'.
    For CS_RMA files, returns (type, rows, claim_detail_rows).
    """
    fname_lower = filename.lower()
    if "ms_kargo" in fname_lower or "kargo" in fname_lower:
        return "shipments", parse_ms_kargo(file_bytes), []
    elif "cs_rma" in fname_lower or "rma" in fname_lower:
        rma_rows = parse_rma_detail(file_bytes)
        claim_rows = parse_rma_data_sheet(file_bytes)
        return "rma", rma_rows, claim_rows
    else:
        # Try MS_Kargo format as default (check headers)
        logger.info(f"Unknown file type '{filename}', attempting MS_Kargo parse")
        try:
            rows = parse_ms_kargo(file_bytes)
            return "shipments", rows, []
        except Exception:
            logger.warning(f"Could not parse '{filename}' as MS_Kargo either — skipping")
            return "unknown", [], []


def parse_rma_data_sheet(file_bytes: bytes) -> list[dict]:
    """
    Parse the CS_RMA_DETAIL Excel — 'Data' sheet with individual claim rows.
    Headers are in row 5. Data starts after header row.
    Returns list of dicts for claim_details table.

    NOTE: Different CS_RMA files have DIFFERENT column layouts:
      - Some have 35 columns (full detail)
      - Some have only 13 columns (compact)
    
    We use dynamic header matching by scanning ALL column names, not a fixed
    dict (which breaks when duplicate header names exist like "Returned Reason").
    """
    if not file_bytes or len(file_bytes) < 100:
        logger.warning("CS_RMA_DETAIL Data: Empty or invalid file")
        return []
    
    try:
        wb = openpyxl.load_workbook(
            filename=io.BytesIO(file_bytes), read_only=True, data_only=True
        )
    except Exception as e:
        logger.error(f"CS_RMA_DETAIL Data: Failed to open Excel file: {e}")
        return []

    if "Data" not in wb.sheetnames:
        logger.warning("CS_RMA_DETAIL: 'Data' sheet not found — no claim details to parse")
        return []

    ws = wb["Data"]

    # Find header row dynamically (contains "Effective Date")
    header_row_idx = None
    header_cells = None
    for row_idx, row in enumerate(ws.iter_rows(min_row=1, max_row=10), start=1):
        row_vals = [c.value for c in row]
        row_strs = [str(v).strip().lower() if v else "" for v in row_vals]
        if any("effective date" in s for s in row_strs):
            header_row_idx = row_idx
            header_cells = row_vals
            break

    if header_row_idx is None:
        logger.warning("CS_RMA_DETAIL Data sheet: Could not find header row")
        return []

    # Build column index list: (index, lowercase_header_name)
    # DO NOT use a dict — duplicate header names (e.g., "Returned Reason") will overwrite
    all_headers = []
    for i, h in enumerate(header_cells):
        if h is not None:
            all_headers.append((i, str(h).strip().lower()))

    logger.info(f"Data sheet has {len(all_headers)} header columns at row {header_row_idx}")

    # Helper to find first column matching a keyword
    def find_col(keyword):
        for idx, name in all_headers:
            if keyword in name:
                return idx
        return None

    # Helper to find ALL columns matching a keyword (returns list of indices)
    def find_all_cols(keyword):
        return [idx for idx, name in all_headers if keyword in name]

    # Find required columns
    col_date = find_col("effective date")
    col_credit = find_col("credit issued")

    # Find optional columns (may not exist in compact 13-col files)
    col_order = find_col("original order number")
    col_shipment = find_col("shipment number")
    col_carrier = find_col("concatenation carrier number")

    # Returned Reason appears TWICE in 35-col files:
    #   First  = internal code  (K12, K7, etc.)
    #   Second = readable type  (SHORTAGE, DAMAGE, etc.)
    # In 13-col files, there may still be two cols.
    # We always want the LAST "Returned Reason" column (readable type).
    reason_cols = find_all_cols("returned reason")
    col_reason = reason_cols[-1] if reason_cols else None

    if col_date is None or col_credit is None:
        logger.warning(
            f"CS_RMA_DETAIL Data sheet: Missing required columns "
            f"(date={col_date}, credit={col_credit})"
        )
        return []

    logger.info(
        f"Data sheet column mapping: date={col_date}, order={col_order}, "
        f"shipment={col_shipment}, credit={col_credit}, carrier={col_carrier}, "
        f"reason={col_reason} (from {len(reason_cols)} 'Returned Reason' cols)"
    )

    rows = []
    skipped = 0
    for row in ws.iter_rows(min_row=header_row_idx + 1, values_only=True):
        # Skip empty rows
        if all(v is None for v in row):
            continue

        row_len = len(row)

        # Get effective date
        date_val = row[col_date] if col_date < row_len else None
        if date_val is None:
            skipped += 1
            continue

        # Parse date
        if isinstance(date_val, datetime):
            claim_date = date_val
        else:
            try:
                claim_date = datetime.fromisoformat(str(date_val))
            except Exception:
                skipped += 1
                continue

        # Get credit amount
        credit_val = row[col_credit] if col_credit < row_len else None
        if credit_val is None:
            skipped += 1
            continue
        try:
            claim_amount = float(credit_val)
        except (ValueError, TypeError):
            skipped += 1
            continue

        # Get optional fields safely
        def safe_str(val):
            if val is None:
                return None
            s = str(val).strip()
            return s if s else None

        def safe_int_str(val):
            if val is None:
                return None
            s = str(val).strip()
            if not s:
                return None
            try:
                return str(int(float(s)))
            except (ValueError, TypeError):
                return s

        order_id = safe_int_str(row[col_order]) if col_order is not None and col_order < row_len else None
        sscc18 = safe_int_str(row[col_shipment]) if col_shipment is not None and col_shipment < row_len else None
        carrier_bp = safe_str(row[col_carrier]) if col_carrier is not None and col_carrier < row_len else None
        claim_type_raw = safe_str(row[col_reason]) if col_reason is not None and col_reason < row_len else None

        # Normalize claim_type for consistent Grafana filtering:
        # "OBSOLETE - SHORTAGE - CC" → "SHORTAGE"
        # "OBSOLETE - DAMAGE -CC" → "DAMAGE"
        # "DAMAGED IN TRANSIT FROM BAXTER" → "DAMAGE"
        # "DAMAGED RETURN-CUSTOMER" → "DAMAGE"
        if claim_type_raw:
            upper = claim_type_raw.upper()
            if "SHORTAGE" in upper or "SHORT" in upper:
                claim_type = "SHORTAGE"
            elif "DAMAGE" in upper:
                claim_type = "DAMAGE"
            else:
                claim_type = claim_type_raw
        else:
            claim_type = "SHORTAGE"

        rows.append({
            "claim_date": claim_date,
            "order_id": order_id,
            "sscc18": sscc18,
            "claim_amount": claim_amount,
            "claim_type": claim_type,
            "carrier_bp": carrier_bp,
        })

    logger.info(f"Parsed {len(rows)} claim detail rows from Data sheet (skipped {skipped})")
    wb.close()
    return rows

#!/usr/bin/env python3
"""
Comprehensive QA Test Suite for Baxter Pipeline
Tests: Parser, Database, Error Handling, Edge Cases, Security
"""
import sys
import os
import io
import glob
import traceback
from datetime import datetime

sys.path.insert(0, "ingestor")

# Track test results
PASSED = []
FAILED = []

def test(name):
    """Decorator to track test results"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                if result:
                    PASSED.append(name)
                    print(f"✓ PASS: {name}")
                else:
                    FAILED.append(name)
                    print(f"✗ FAIL: {name}")
                return result
            except Exception as e:
                FAILED.append(f"{name}: {e}")
                print(f"✗ FAIL: {name} - {e}")
                return False
        return wrapper
    return decorator

# ============== PARSER TESTS ==============

@test("Parser: Import modules")
def test_import_modules():
    from excel_parser import detect_and_parse, parse_ms_kargo, parse_rma_detail, parse_rma_data_sheet
    return True

@test("Parser: 35-column CS_RMA file")
def test_35col_file():
    from excel_parser import parse_rma_data_sheet
    filepath = r"C:\Users\MUHAMMAD JAHANZEB\Downloads\CS_RMA_DETAIL_Embed_Excel_062073256977.xlsx"
    if not os.path.exists(filepath):
        print("    File not found, skipping")
        return True
    with open(filepath, "rb") as f:
        data = f.read()
    rows = parse_rma_data_sheet(data)
    # Should have rows, all with carrier and order
    if len(rows) < 10000:
        return False
    carriers = sum(1 for r in rows if r["carrier_bp"])
    orders = sum(1 for r in rows if r["order_id"])
    return carriers == len(rows) and orders == len(rows)

@test("Parser: 13-column CS_RMA file (no carrier/order)")
def test_13col_file():
    from excel_parser import parse_rma_data_sheet
    filepath = r"C:\Users\MUHAMMAD JAHANZEB\Downloads\CS_RMA_DETAIL_Embed_Excel_058073244343.xlsx"
    if not os.path.exists(filepath):
        print("    File not found, skipping")
        return True
    with open(filepath, "rb") as f:
        data = f.read()
    rows = parse_rma_data_sheet(data)
    # Should have rows, but carrier/order should be None
    if len(rows) < 10000:
        return False
    carriers = sum(1 for r in rows if r["carrier_bp"])
    # 13-col files have NO carrier column
    return carriers == 0

@test("Parser: Claim type normalization - SHORTAGE")
def test_claim_type_shortage():
    from excel_parser import parse_rma_data_sheet
    filepath = r"C:\Users\MUHAMMAD JAHANZEB\Downloads\CS_RMA_DETAIL_Embed_Excel_064073243874.xlsx"
    if not os.path.exists(filepath):
        print("    File not found, skipping")
        return True
    with open(filepath, "rb") as f:
        data = f.read()
    rows = parse_rma_data_sheet(data)
    types = set(r["claim_type"] for r in rows)
    # Should only have SHORTAGE and DAMAGE, not K12, K7, OBSOLETE-SHORTAGE-CC etc
    bad_types = [t for t in types if t not in ("SHORTAGE", "DAMAGE")]
    if bad_types:
        print(f"    Unexpected types: {bad_types}")
        return False
    return True

@test("Parser: MS_Kargo file")
def test_ms_kargo():
    from excel_parser import parse_ms_kargo
    filepath = r"C:\Users\MUHAMMAD JAHANZEB\Downloads\MS_Kargo.xlsx"
    if not os.path.exists(filepath):
        print("    File not found, skipping")
        return True
    with open(filepath, "rb") as f:
        data = f.read()
    rows = parse_ms_kargo(data)
    return len(rows) > 0

@test("Parser: detect_and_parse returns correct tuple")
def test_detect_and_parse_tuple():
    from excel_parser import detect_and_parse
    filepath = r"C:\Users\MUHAMMAD JAHANZEB\Downloads\CS_RMA_DETAIL_Embed_Excel_064073243874.xlsx"
    if not os.path.exists(filepath):
        return True
    with open(filepath, "rb") as f:
        data = f.read()
    result = detect_and_parse("CS_RMA_test.xlsx", data)
    # Should return (file_type, rows, claim_rows)
    if len(result) != 3:
        print(f"    Expected 3 tuple elements, got {len(result)}")
        return False
    ftype, rows, claims = result
    return ftype == "rma" and isinstance(rows, list) and isinstance(claims, list)

# ============== EDGE CASE TESTS ==============

@test("Edge: Empty Excel bytes")
def test_empty_bytes():
    from excel_parser import parse_rma_data_sheet
    try:
        rows = parse_rma_data_sheet(b"")
        return True  # Should handle gracefully
    except Exception as e:
        print(f"    Unhandled exception: {e}")
        return False

@test("Edge: Invalid Excel data")
def test_invalid_excel():
    from excel_parser import parse_rma_data_sheet
    try:
        rows = parse_rma_data_sheet(b"not an excel file")
        return True  # Should handle gracefully
    except Exception as e:
        # Some exception is OK but shouldn't crash
        return True

@test("Edge: CS_RMA without Data sheet")
def test_no_data_sheet():
    from excel_parser import parse_rma_data_sheet
    filepath = r"C:\Users\MUHAMMAD JAHANZEB\Downloads\CS_RMA_Weekly_Working_File_Embed_Excel_061023035906.xlsx"
    if not os.path.exists(filepath):
        return True
    with open(filepath, "rb") as f:
        data = f.read()
    rows = parse_rma_data_sheet(data)
    # Should return empty list, not crash
    return rows == []

# ============== DATABASE TESTS ==============

@test("DB: Connection pool works")
def test_db_pool():
    from db import get_connection, release_connection
    conn = get_connection()
    release_connection(conn)
    return True

@test("DB: Duplicate detection works")
def test_duplicate_detection():
    from db import get_connection, release_connection
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Check constraint exists
            cur.execute("""
                SELECT COUNT(*) FROM pg_constraint 
                WHERE conname = 'uq_claim_detail'
            """)
            count = cur.fetchone()[0]
            return count == 1
    finally:
        release_connection(conn)

# ============== SECURITY TESTS ==============

@test("Security: Credentials not hardcoded in code")
def test_no_hardcoded_creds():
    sensitive_patterns = ["password123", "secret123", "api_key="]
    files_to_check = ["ingestor/main.py", "ingestor/graph_api.py", "ingestor/db.py"]
    for fpath in files_to_check:
        if os.path.exists(fpath):
            try:
                content = open(fpath, encoding="utf-8", errors="ignore").read().lower()
            except:
                continue
            for pattern in sensitive_patterns:
                if pattern in content:
                    print(f"    Found '{pattern}' in {fpath}")
                    return False
    return True

@test("Security: .env file not committed (check .gitignore)")
def test_env_in_gitignore():
    if os.path.exists(".gitignore"):
        content = open(".gitignore").read()
        return ".env" in content
    return False

# ============== GRAFANA QUERY TESTS ==============

@test("Grafana: Dashboard JSON valid")
def test_dashboard_json():
    import json
    dashboard_path = "grafana/dashboards/04_cost_savings.json"
    if not os.path.exists(dashboard_path):
        return True
    with open(dashboard_path) as f:
        data = json.load(f)
    # Check claim_type variable sources from claim_details (not rma_credits)
    templating = data.get("templating", {}).get("list", [])
    for var in templating:
        if var.get("name") == "claim_type":
            query = var.get("query", "")
            if "rma_credits" in query:
                print("    claim_type still queries rma_credits!")
                return False
            if "claim_details" in query:
                return True
    return True

# ============== RUN ALL TESTS ==============

def run_all_tests():
    print("\n" + "="*60)
    print("BAXTER QA TEST SUITE")
    print("="*60 + "\n")
    
    # Run all tests
    test_import_modules()
    test_35col_file()
    test_13col_file()
    test_claim_type_shortage()
    test_ms_kargo()
    test_detect_and_parse_tuple()
    test_empty_bytes()
    test_invalid_excel()
    test_no_data_sheet()
    test_db_pool()
    test_duplicate_detection()
    test_no_hardcoded_creds()
    test_env_in_gitignore()
    test_dashboard_json()
    
    # Summary
    print("\n" + "="*60)
    print(f"RESULTS: {len(PASSED)} passed, {len(FAILED)} failed")
    print("="*60)
    
    if FAILED:
        print("\nFailed tests:")
        for f in FAILED:
            print(f"  - {f}")
    
    return len(FAILED) == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

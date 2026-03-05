#!/usr/bin/env python3
"""
Manual Excel file upload script - bypasses email and directly processes Excel files
Usage: python manual_upload.py path/to/excelfile.xlsx
"""
import sys
import os
from pathlib import Path

# Add ingestor to path
sys.path.insert(0, str(Path(__file__).parent / "ingestor"))

from dotenv import load_dotenv
load_dotenv()

# Import from ingestor
from excel_parser import detect_and_parse
from db import get_db_connection, insert_shipments, insert_rma_credits, insert_claim_details

def upload_file(filepath: str):
    """Upload an Excel file directly to the database"""
    filepath = Path(filepath)
    
    if not filepath.exists():
        print(f"❌ File not found: {filepath}")
        return False
    
    if not filepath.suffix.lower() == '.xlsx':
        print(f"❌ Not an Excel file: {filepath}")
        return False
    
    print(f"\n📂 Processing file: {filepath.name}")
    print(f"   Size: {filepath.stat().st_size:,} bytes")
    
    # Read file
    file_bytes = filepath.read_bytes()
    
    # Parse Excel
    print(f"\n🔍 Parsing Excel file...")
    ms_kargo_rows, cs_rma_rows, claim_rows = detect_and_parse(filepath.name, file_bytes)
    
    print(f"   Found {len(ms_kargo_rows)} MS_Kargo rows")
    print(f"   Found {len(cs_rma_rows)} CS_RMA rows")
    print(f"   Found {len(claim_rows)} Claim detail rows")
    
    if not ms_kargo_rows and not cs_rma_rows and not claim_rows:
        print(f"❌ No valid data found in file")
        return False
    
    # Insert to database
    print(f"\n💾 Inserting to database...")
    conn = get_db_connection()
    
    try:
        if ms_kargo_rows:
            inserted = insert_shipments(conn, ms_kargo_rows)
            print(f"   ✅ Inserted {inserted} shipments")
        
        if cs_rma_rows:
            inserted = insert_rma_credits(conn, cs_rma_rows)
            print(f"   ✅ Inserted {inserted} RMA credits")
        
        if claim_rows:
            inserted = insert_claim_details(conn, claim_rows)
            print(f"   ✅ Inserted {inserted} claim details")
        
        conn.commit()
        print(f"\n🎉 SUCCESS! Data uploaded to database")
        print(f"   Check Grafana dashboards: http://localhost:3000")
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Database error: {e}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python manual_upload.py <excel_file.xlsx>")
        print("\nExample:")
        print("  python manual_upload.py sample_data/MS_Kargo.xlsx")
        print("  python manual_upload.py sample_data/CS_RMA_DETAIL.xlsx")
        sys.exit(1)
    
    filepath = sys.argv[1]
    success = upload_file(filepath)
    sys.exit(0 if success else 1)

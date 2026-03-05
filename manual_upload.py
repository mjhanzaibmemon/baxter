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
from db import insert_shipments, insert_rma_credits, insert_claim_details

def upload_file(filepath: str):
    """Upload an Excel file directly to the database"""
    filepath = Path(filepath)
    
    if not filepath.exists():
        print(f"File not found: {filepath}")
        return False
    
    if not filepath.suffix.lower() == '.xlsx':
        print(f"Not an Excel file: {filepath}")
        return False
    
    print(f"\nProcessing file: {filepath.name}")
    print(f"  Size: {filepath.stat().st_size:,} bytes")
    
    # Read file
    file_bytes = filepath.read_bytes()
    
    # Parse Excel
    print(f"\nParsing Excel file...")
    file_type, rows, claim_rows = detect_and_parse(filepath.name, file_bytes)
    
    print(f"  File type: {file_type}")
    print(f"  Primary rows: {len(rows)}")
    print(f"  Claim detail rows: {len(claim_rows)}")
    
    if not rows and not claim_rows:
        print(f"No valid data found in file")
        return False
    
    # Insert to database
    source = filepath.name
    print(f"\nInserting to database...")
    
    try:
        if file_type == "shipments" and rows:
            inserted = insert_shipments(rows, source)
            print(f"  Inserted {inserted} shipments")
        
        if file_type == "rma" and rows:
            inserted = insert_rma_credits(rows, source)
            print(f"  Inserted {inserted} RMA credits")
        
        if claim_rows:
            inserted = insert_claim_details(claim_rows, source)
            print(f"  Inserted {inserted} claim details")
        
        print(f"\nSUCCESS! Data uploaded to database")
        print(f"  Check Grafana dashboards: http://localhost:3000")
        return True
        
    except Exception as e:
        print(f"\nDatabase error: {e}")
        return False


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

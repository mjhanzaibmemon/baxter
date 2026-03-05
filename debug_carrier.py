#!/usr/bin/env python3
"""Debug carrier extraction issue"""
import sys
sys.path.insert(0, 'ingestor')

from excel_parser import detect_and_parse
from pathlib import Path

filepath = r"C:\Users\MUHAMMAD JAHANZEB\Downloads\CS_RMA_DETAIL_Embed_Excel_058073244343.xlsx"
file_bytes = Path(filepath).read_bytes()

ms_kargo, cs_rma, claims = detect_and_parse("CS_RMA_DETAIL.xlsx", file_bytes)

print(f"✅ Parsed {len(claims)} claim records\n")

# Check carrier values
carriers_with_data = [c for c in claims if c.get('carrier_bp')]
carriers_null = [c for c in claims if not c.get('carrier_bp')]

print(f"Records WITH carrier data: {len(carriers_with_data)}")
print(f"Records WITHOUT carrier data (NULL): {len(carriers_null)}")

if carriers_with_data:
    print(f"\nSample records WITH carrier:")
    for i, c in enumerate(carriers_with_data[:3], 1):
        print(f"  {i}. Carrier: {c.get('carrier_bp')}")
        print(f"     Amount: ${c.get('claim_amount')}")
        print(f"     Type: {c.get('claim_type')}")

# Also check order_id and sscc18
orders_with_data = [c for c in claims if c.get('order_id')]
sscc_with_data = [c for c in claims if c.get('sscc18')]

print(f"\nRecords WITH order_id: {len(orders_with_data)}")
print(f"Records WITH sscc18: {len(sscc_with_data)}")

if orders_with_data:
    print(f"\nSample order_id values:")
    for i, c in enumerate(orders_with_data[:3], 1):
        print(f"  {i}. Order: {c.get('order_id')}, SSCC18: {c.get('sscc18')}")

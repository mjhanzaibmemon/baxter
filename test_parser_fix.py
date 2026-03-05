#!/usr/bin/env python3
"""Quick test of the parser fix - check claim_type values"""
import sys
sys.path.insert(0, 'ingestor')

from excel_parser import detect_and_parse
from pathlib import Path

filepath = r"C:\Users\MUHAMMAD JAHANZEB\Downloads\CS_RMA_DETAIL_Embed_Excel_058073244343.xlsx"
file_bytes = Path(filepath).read_bytes()

ms_kargo, cs_rma, claims = detect_and_parse("CS_RMA_DETAIL.xlsx", file_bytes)

print(f"\n✅ Parsed {len(claims)} claim detail rows\n")

# Check unique claim_type values
claim_types = set()
for c in claims:
    if c.get('claim_type'):
        claim_types.add(c['claim_type'])

print(f"Unique claim_type values found:")
for ct in sorted(claim_types):
    count = sum(1 for c in claims if c.get('claim_type') == ct)
    print(f"  {ct!r}: {count} records")

print(f"\nFirst 5 claim records:")
for i, claim in enumerate(claims[:5], 1):
    print(f"\n  Record {i}:")
    print(f"    Date: {claim.get('claim_date')}")
    print(f"    Amount: ${claim.get('claim_amount')}")
    print(f"    Type: {claim.get('claim_type')!r}")
    print(f"    Carrier: {claim.get('carrier_bp')}")

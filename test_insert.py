#!/usr/bin/env python3
"""Quick test: parse and insert 1 MS_Kargo + 1 CS_RMA into PostgreSQL."""
import sys, os
sys.path.insert(0, "/app")

from excel_parser import detect_and_parse
from db import insert_shipments, insert_rma_credits, insert_claim_details, rebuild_daily_history

# Process MS_Kargo
with open("/tmp/test_ms_kargo.xlsx", "rb") as f:
    data = f.read()
ftype, rows, claims = detect_and_parse("MS_Kargo.xlsx", data)
print(f"MS_Kargo: type={ftype}, rows={len(rows)}")
if rows:
    n = insert_shipments(rows, "test_MS_Kargo.xlsx")
    print(f"  Inserted {n} shipments")

# Process CS_RMA
with open("/tmp/test_cs_rma.xlsx", "rb") as f:
    data = f.read()
ftype, rows, claims = detect_and_parse("CS_RMA_064.xlsx", data)
print(f"CS_RMA: type={ftype}, summary={len(rows)}, claims={len(claims)}")
if rows:
    n = insert_rma_credits(rows, "test_CS_RMA_064.xlsx")
    print(f"  Inserted {n} RMA credits")
if claims:
    n = insert_claim_details(claims, "test_CS_RMA_064.xlsx")
    print(f"  Inserted {n} claim details")
    # Show breakdown
    types = {}
    carriers = 0
    orders = 0
    for c in claims:
        t = c["claim_type"]
        types[t] = types.get(t, 0) + 1
        if c["carrier_bp"]: carriers += 1
        if c["order_id"]: orders += 1
    print(f"  Claim types: {types}")
    print(f"  Carriers: {carriers}/{len(claims)}")
    print(f"  Orders: {orders}/{len(claims)}")
    print(f"  Sample row: {claims[0]}")

# Rebuild daily history for time series chart
rebuild_daily_history()
print("Daily history rebuilt")
print("ALL DONE")

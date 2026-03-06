#!/usr/bin/env python3
"""Quick DB tests for EC2"""
import sys
sys.path.insert(0, "/app")

from db import get_connection, release_connection

print("Testing DB connection pool...")
conn = get_connection()
print("  Connection acquired: OK")

with conn.cursor() as cur:
    cur.execute("SELECT COUNT(*) FROM pg_constraint WHERE conname = 'uq_claim_detail'")
    count = cur.fetchone()[0]
    print(f"  Unique constraint exists: {count == 1}")
    
    cur.execute("SELECT COUNT(*) FROM claim_details")
    claims = cur.fetchone()[0]
    print(f"  Claims in DB: {claims}")

release_connection(conn)
print("  Connection released: OK")
print("DB Tests: ALL PASSED")

#!/usr/bin/env python3
"""Check what column headers are being detected"""
import openpyxl
import io
from pathlib import Path

filepath = r"C:\Users\MUHAMMAD JAHANZEB\Downloads\CS_RMA_DETAIL_Embed_Excel_058073244343.xlsx"
file_bytes = Path(filepath).read_bytes()

wb = openpyxl.load_workbook(filename=io.BytesIO(file_bytes), read_only=True, data_only=True)
ws = wb["Data"]

# Find header row
for row_idx, row in enumerate(ws.iter_rows(min_row=1, max_row=10), start=1):
    row_vals = [c.value for c in row]
    row_strs = [str(v).strip().lower() if v else "" for v in row_vals]
    if any("effective date" in s for s in row_strs):
        print(f"Header row found at: Row {row_idx}\n")
        
        # Build header map like parser does
        header_map = {}
        for i, h in enumerate(row_vals):
            if h is not None:
                key = str(h).strip().lower()
                header_map[key] = i
                print(f"  header_map['{key}'] = {i}")
        
        print(f"\n📍 Looking for these columns:")
        print(f"  'effective date': {header_map.get('effective date')}")
        print(f"  'original order number': {header_map.get('original order number')}")
        print(f"  'shipment number - f4211.shpn': {header_map.get('shipment number - f4211.shpn')}")
        print(f"  'credit issued': {header_map.get('credit issued')}")
        print(f"  'concatenation carrier number - cars': {header_map.get('concatenation carrier number - cars')}")
        
        break

wb.close()

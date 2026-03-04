import openpyxl
wb = openpyxl.load_workbook('sample_data/CS_RMA_DETAIL_Embed_Excel_061073437323.xlsx', data_only=True)
sheet = wb['Data']
headers = [c.value for c in sheet[5]]
for i, h in enumerate(headers):
    if h is not None:
        print(f"  Col {i}: {h}")

print(f"\nTotal columns with data: {len([h for h in headers if h])}")

# Also check a data row
row6 = [c.value for c in sheet[6]]
print("\nSample data row (row 6):")
for i, (h, v) in enumerate(zip(headers, row6)):
    if h is not None:
        print(f"  {h}: {v}")

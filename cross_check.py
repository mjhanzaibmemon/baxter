import csv

# Load Result_27.csv (shipments)
r27_orders = {}
r27_sscc = set()
with open('sample_data/Result_27.csv') as f:
    for row in csv.DictReader(f):
        r27_orders[row['order_number']] = True
        r27_sscc.add(row['sscc18'])

# Load AllOrders.csv
ao = {}
ao_lpns = set()
with open('sample_data/AllOrders.csv') as f:
    for row in csv.DictReader(f):
        ao[row['Order_Number']] = row['Order_Status']
        if row['Missed_LPNs']:
            for lpn in row['Missed_LPNs'].split(','):
                ao_lpns.add(lpn.strip())

# Cross-reference orders
both = [k for k in ao if k in r27_orders]
short_match = [k for k in both if ao[k] == 'Short']
perfect_match = [k for k in both if ao[k] == 'Perfect']

print(f"Result_27 unique orders: {len(r27_orders)}")
print(f"AllOrders unique orders: {len(ao)}")
print(f"Orders in BOTH: {len(both)}")
print(f"  - Short in both: {len(short_match)}")
print(f"  - Perfect in both: {len(perfect_match)}")
print()

# Cross-reference SSCC18/LPNs
sscc_both = ao_lpns & r27_sscc
print(f"Result_27 unique SSCC18: {len(r27_sscc)}")
print(f"AllOrders unique LPNs: {len(ao_lpns)}")
print(f"SSCC18/LPNs in BOTH: {len(sscc_both)}")
print()

# Also check Excel claim_details for matching
print("Sample matching Short orders:")
for o in short_match[:10]:
    print(f"  {o}")
print()
print("Sample matching SSCC18:")
for s in list(sscc_both)[:10]:
    print(f"  {s}")

# Only in AllOrders
only_ao = [k for k in ao if k not in r27_orders]
print(f"\nOrders ONLY in AllOrders (not in Result_27): {len(only_ao)}")
print(f"Orders ONLY in Result_27 (not in AllOrders): {len(r27_orders) - len(both) + len(ao) - len(ao)}")

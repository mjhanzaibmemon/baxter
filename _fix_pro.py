import os

files = [
    r'c:\Users\MUHAMMAD JAHANZEB\Desktop\paul-demo-pipeline\grafana\dashboards\01_volume_over_time.json',
    r'c:\Users\MUHAMMAD JAHANZEB\Desktop\paul-demo-pipeline\grafana\dashboards\02_shipment_order_breakdown.json',
    r'c:\Users\MUHAMMAD JAHANZEB\Desktop\paul-demo-pipeline\grafana\dashboards\04_claim_validation.json',
]

patterns = [
    " AND s.pro_number IS NOT NULL AND s.pro_number <> ''",
    " AND pro_number IS NOT NULL AND pro_number <> ''",
]

for f in files:
    with open(f, 'r', encoding='utf-8') as fh:
        content = fh.read()
    total = 0
    for p in patterns:
        c = content.count(p)
        total += c
        content = content.replace(p, '')
    with open(f, 'w', encoding='utf-8') as fh:
        fh.write(content)
    print(f'{os.path.basename(f)}: {total} replacements')

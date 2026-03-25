import os

path = r'c:\Users\MUHAMMAD JAHANZEB\Desktop\paul-demo-pipeline\grafana\dashboards'
for fname in ['01_volume_over_time.json','02_shipment_order_breakdown.json','04_claim_validation.json']:
    fp = os.path.join(path, fname)
    with open(fp, 'r', encoding='utf-8') as f:
        content = f.read()
    # Remove all pro_number filter patterns (various forms)
    content = content.replace(" AND pro_number IS NOT NULL AND pro_number <> ''", '')
    content = content.replace(" AND s.pro_number IS NOT NULL AND s.pro_number <> ''", '')
    content = content.replace("s.pro_number IS NOT NULL AND s.pro_number <> '' AND ", '')
    content = content.replace("pro_number IS NOT NULL AND pro_number <> '' AND ", '')
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(content)
    count = content.count('pro_number')
    print(f'{fname}: remaining pro_number refs = {count}')

#!/bin/bash
echo "=== DASHBOARD VERIFICATION ==="
echo ""
echo "--- DB04: Orders Shipped (6 carriers) ---"
sudo docker exec baxter_postgres psql -U baxter -d baxter_demo -t -c "SELECT COUNT(DISTINCT order_id) FROM shipments WHERE scac IN ('FXFE','HSNR','HSND','HSNC','HSNN','HSNA')"

echo "--- DB04: Claims Submitted (SHORTAGE, any carrier) ---"
sudo docker exec baxter_postgres psql -U baxter -d baxter_demo -t -c "SELECT COUNT(*) FROM claim_details WHERE claim_type = 'SHORTAGE'"

echo "--- DB04: Verified Shortages ---"
sudo docker exec baxter_postgres psql -U baxter -d baxter_demo -t -c "SELECT COUNT(*) FROM claim_details c WHERE c.claim_type='SHORTAGE' AND EXISTS(SELECT 1 FROM shipments s WHERE ('FXFE' = s.scac OR 'HSNR' = s.scac OR 'HSND' = s.scac OR 'HSNC' = s.scac OR 'HSNN' = s.scac OR 'HSNA' = s.scac) AND ((c.sscc18 IS NOT NULL AND c.sscc18 <> '' AND s.sscc18=c.sscc18) OR ((c.sscc18 IS NULL OR c.sscc18='') AND c.order_id IS NOT NULL AND c.order_id <> '' AND s.order_id=c.order_id)))"

echo "--- DB04: Invalid Claims ---"
sudo docker exec baxter_postgres psql -U baxter -d baxter_demo -t -c "SELECT COUNT(*) FROM claim_details c WHERE c.claim_type='SHORTAGE' AND NOT EXISTS(SELECT 1 FROM shipments s WHERE ('FXFE' = s.scac OR 'HSNR' = s.scac OR 'HSND' = s.scac OR 'HSNC' = s.scac OR 'HSNN' = s.scac OR 'HSNA' = s.scac) AND ((c.sscc18 IS NOT NULL AND c.sscc18 <> '' AND s.sscc18=c.sscc18) OR ((c.sscc18 IS NULL OR c.sscc18='') AND c.order_id IS NOT NULL AND c.order_id <> '' AND s.order_id=c.order_id)))"

echo ""
echo "--- DB02: Total Barcode Scans (6 carriers) ---"
sudo docker exec baxter_postgres psql -U baxter -d baxter_demo -t -c "SELECT COUNT(*) FROM shipments WHERE scac IN ('FXFE','HSNR','HSND','HSNC','HSNN','HSNA')"

echo "--- DB02: Unique Carriers (6 carriers) ---"
sudo docker exec baxter_postgres psql -U baxter -d baxter_demo -t -c "SELECT COUNT(DISTINCT scac) FROM shipments WHERE scac IN ('FXFE','HSNR','HSND','HSNC','HSNN','HSNA')"

echo "--- DB02: Unique Orders (6 carriers) ---"
sudo docker exec baxter_postgres psql -U baxter -d baxter_demo -t -c "SELECT COUNT(DISTINCT order_id) FROM shipments WHERE scac IN ('FXFE','HSNR','HSND','HSNC','HSNN','HSNA')"

echo "--- DB02: Total Claim $ (SHORTAGE) ---"
sudo docker exec baxter_postgres psql -U baxter -d baxter_demo -t -c "SELECT SUM(ABS(claim_amount)) FROM claim_details WHERE claim_type = 'SHORTAGE'"

echo "--- DB02: Total Claim Count (SHORTAGE) ---"
sudo docker exec baxter_postgres psql -U baxter -d baxter_demo -t -c "SELECT COUNT(*) FROM claim_details WHERE claim_type = 'SHORTAGE'"

echo ""
echo "--- DB01: Total Shipments (6 carriers) ---"
sudo docker exec baxter_postgres psql -U baxter -d baxter_demo -t -c "SELECT COUNT(*) FROM shipments WHERE scac IN ('FXFE','HSNR','HSND','HSNC','HSNN','HSNA')"

echo "--- DB01: Unique Carriers ---"
sudo docker exec baxter_postgres psql -U baxter -d baxter_demo -t -c "SELECT COUNT(DISTINCT scac) FROM shipments WHERE scac IN ('FXFE','HSNR','HSND','HSNC','HSNN','HSNA')"

echo "--- DB01: Unique Orders ---"
sudo docker exec baxter_postgres psql -U baxter -d baxter_demo -t -c "SELECT COUNT(DISTINCT order_id) FROM shipments WHERE scac IN ('FXFE','HSNR','HSND','HSNC','HSNN','HSNA')"

echo ""
echo "=== DONE ==="

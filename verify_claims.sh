#!/bin/bash
sudo docker exec baxter_postgres psql -U baxter -d baxter_demo -c "SELECT count(*) as claim_count, ROUND(SUM(claim_amount)::numeric, 2) as total_claim_dollars FROM claim_details WHERE claim_type = 'SHORTAGE';"
echo "---"
sudo docker exec baxter_postgres psql -U baxter -d baxter_demo -c "SELECT count(*) as total_scans FROM shipments;"

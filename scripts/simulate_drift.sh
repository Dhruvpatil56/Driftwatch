#!/bin/bash
set -e

INSTANCE_ID="i-08bbbeb680e86a500"
SG_ID="sg-032a91de65677f051"
BUCKET="driftwatch-demo-data"
REGION="ap-south-1"

echo "=== DriftWatch — Simulating Drift ==="

echo ""
echo "--- Scenario 1: EC2 Instance Type (Infrastructure Drift) ---"
aws ec2 stop-instances --instance-ids $INSTANCE_ID --region $REGION
aws ec2 wait instance-stopped --instance-ids $INSTANCE_ID --region $REGION
aws ec2 modify-instance-attribute --instance-id $INSTANCE_ID --instance-type t3.small --region $REGION
aws ec2 start-instances --instance-ids $INSTANCE_ID --region $REGION
echo "EC2 changed to t3.small"

echo ""
echo "--- Scenario 2: SG Port 22 Injection (Configuration Drift) ---"
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 22 \
  --cidr 0.0.0.0/0 \
  --region $REGION
echo "Port 22 open to 0.0.0.0/0 added to SG"

echo ""
echo "--- Scenario 3: S3 Tag Drift (Configuration Drift) ---"
aws s3api put-bucket-tagging \
  --bucket $BUCKET \
  --tagging 'TagSet=[{Key=Name,Value=driftwatch-demo-data},{Key=Environment,Value=hacked}]' \
  --region $REGION
echo "Rogue tag Environment=hacked added to S3 bucket"

echo ""
echo "=== All drift scenarios applied. Running DriftWatch ==="
cd ~/driftwatch
source ~/driftwatch-venv/bin/activate
python main.py

#!/bin/bash
set -e

INSTANCE_ID="i-08bbbeb680e86a500"
SG_ID="sg-032a91de65677f051"
BUCKET="driftwatch-demo-data"
REGION="ap-south-1"

echo "=== DriftWatch — Restoring Clean State ==="

echo ""
echo "--- Restoring EC2 to t3.micro ---"
aws ec2 stop-instances --instance-ids $INSTANCE_ID --region $REGION
aws ec2 wait instance-stopped --instance-ids $INSTANCE_ID --region $REGION
aws ec2 modify-instance-attribute --instance-id $INSTANCE_ID --instance-type t3.micro --region $REGION
aws ec2 start-instances --instance-ids $INSTANCE_ID --region $REGION
echo "EC2 restored to t3.micro"

echo ""
echo "--- Removing Port 22 from SG ---"
aws ec2 revoke-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 22 \
  --cidr 0.0.0.0/0 \
  --region $REGION
echo "Port 22 rule removed"

echo ""
echo "--- Restoring S3 tags ---"
aws s3api put-bucket-tagging \
  --bucket $BUCKET \
  --tagging 'TagSet=[{Key=Name,Value=driftwatch-demo-data}]' \
  --region $REGION
echo "S3 tags restored"

echo ""
echo "=== Clean state restored. Running DriftWatch ==="
cd ~/driftwatch
source ~/driftwatch-venv/bin/activate
python main.py

provider "aws" {
  region = "ap-south-1"
}

resource "aws_instance" "web" {
  ami           = "ami-07a00cf47dbbc844c"
  instance_type = "t3.micro"

  tags = {
    Name        = "driftwatch-web"
    Environment = "demo"
  }
}

resource "aws_security_group" "web_sg" {
  name        = "driftwatch-web-sg"
  description = "DriftWatch demo security group"

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_s3_bucket" "data" {
  bucket = "driftwatch-demo-data"

  tags = {
    Name = "driftwatch-demo-data"
  }
}


# --- DriftWatch proposed remediation (review before merge) ---
# DriftWatch remediation for aws_security_group.web_sg
# ingress: tcp:443-443:0.0.0.0/0 -> tcp:22-22:0.0.0.0/0, tcp:3389-3389:0.0.0.0/0, tcp:443-443:0.0.0.0/0
resource "aws_security_group" "web_sg" {
  ingress = "tcp:22-22:0.0.0.0/0, tcp:3389-3389:0.0.0.0/0, tcp:443-443:0.0.0.0/0"
}

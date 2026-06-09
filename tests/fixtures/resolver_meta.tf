# Test fixture for the resource resolver — count + for_each expansion.
# Fake but valid-format AMI IDs only; never real AWS IDs.

resource "aws_instance" "web" {
  count         = 3
  ami           = "ami-0resolver00000001"
  instance_type = "t3.micro"
}

resource "aws_instance" "env" {
  for_each      = { prod = "t3.large", staging = "t3.micro" }
  ami           = "ami-0resolver00000002"
  instance_type = each.value
}

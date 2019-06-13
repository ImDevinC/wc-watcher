resource "aws_dynamodb_table" "main" {
  name           = "${local.name}"
  hash_key       = "match_id"
  range_key      = "event_id"
  write_capacity = "${var.write_capacity}"
  read_capacity  = "${var.read_capacity}"

  attribute {
    name = "match_id"
    type = "N"
  }

  attribute {
    name = "event_id"
    type = "N"
  }
}

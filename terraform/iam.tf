resource "aws_iam_role" "main" {
  name               = "${local.name}"
  assume_role_policy = "${data.aws_iam_policy_document.assume.json}"
}

resource "aws_iam_policy" "main" {
  name   = "${local.name}"
  policy = "${data.aws_iam_policy_document.main.json}"
}

resource "aws_iam_role_policy_attachment" "main" {
  role       = "${aws_iam_role.main.name}"
  policy_arn = "${aws_iam_policy.main.arn}"
}

data "aws_iam_policy_document" "assume" {
  statement {
    effect = "Allow"

    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "main" {
  statement {
    effect = "Allow"

    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]

    resources = ["*"]
  }

  statement {
    effect = "Allow"

    actions = [
      "dynamodb:BatchWriteItem",
      "dynamodb:PutItem",
      "dynamodb:GetItem",
      "dynamodb:Query",
    ]

    resources = ["${aws_dynamodb_table.main.arn}"]
  }
}

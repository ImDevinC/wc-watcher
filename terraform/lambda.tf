resource "aws_lambda_function" "main" {
  filename         = "../deployment.zip"
  function_name    = "${local.name}"
  role             = "${aws_iam_role.main.arn}"
  handler          = "soccerbot.main"
  source_code_hash = "${base64sha256(file("../deployment.zip"))}"
  runtime          = "python3.7"

  environment {
    variables {
      COMPETITION       = "${var.competition}"
      LOG_LEVEL         = "${var.log_level}"
      WEBHOOK_URL       = "${var.webhook_url}"
      CHANNEL           = "${var.channel}"
      BOT_NAME          = "${var.bot_name}"
      ICON_EMOJI        = "${var.icon_emoji}"
      DYNAMO_TABLE_NAME = "${aws_dynamodb_table.main.name}"
    }
  }
}

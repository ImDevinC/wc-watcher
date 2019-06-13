resource "aws_cloudwatch_event_rule" "daily" {
  name                = "${local.name}-daily-matches"
  is_enabled          = "${var.daily_matches_enabled}"
  schedule_expression = "cron(${var.daily_matches_expression})"
  description         = "Runs daily match check for ${local.name}"
}

resource "aws_cloudwatch_event_target" "daily" {
  rule  = "${aws_cloudwatch_event_rule.daily.id}"
  arn   = "${aws_lambda_function.main.arn}"
  input = "{\"type\": \"daily_matches\"}"
}

resource "aws_lambda_permission" "daily" {
  action        = "lambda:InvokeFunction"
  function_name = "${aws_lambda_function.main.function_name}"
  principal     = "events.amazonaws.com"
  source_arn    = "${aws_cloudwatch_event_rule.daily.arn}"
}

resource "aws_cloudwatch_event_rule" "updates" {
  name                = "${local.name}-match-updates"
  is_enabled          = "${var.updates_enabled}"
  schedule_expression = "cron(${var.updates_expression})"
  description         = "Runs match updates check for ${local.name}"
}

resource "aws_cloudwatch_event_target" "updates" {
  rule  = "${aws_cloudwatch_event_rule.updates.id}"
  arn   = "${aws_lambda_function.main.arn}"
  input = "{\"type\": \"updates\"}"
}

resource "aws_lambda_permission" "updates" {
  action        = "lambda:InvokeFunction"
  function_name = "${aws_lambda_function.main.function_name}"
  principal     = "events.amazonaws.com"
  source_arn    = "${aws_cloudwatch_event_rule.updates.arn}"
}

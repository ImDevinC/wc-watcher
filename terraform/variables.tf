# Required variables
variable "competition" {
  default = 103 # Womens World Cup
}

variable "webhook_url" {
  default = ""
}

variable "log_level" {
  default = "info"
}

# Cloudwatch Rules
variable "daily_matches_enabled" {
  default = true
}

variable "daily_matches_expression" {
  default = "0 8 ? * * *"
}

variable "updates_enabled" {
  default = true
}

variable "updates_expression" {
  default = "* * ? * * *"
}

# Optional Settings
variable "channel" {
  default = ""
}

variable bot_name {
  default = ""
}

variable icon_emoji {
  default = ""
}

# AWS configuration
variable "region" {
  default = "us-east-1"
}

variable "read_capacity" {
  default = 5
}

variable "write_capacity" {
  default = 5
}

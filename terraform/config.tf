provider "aws" {
  region = "${var.region}"
}

terraform {
  backend "s3" {
    key            = "wc-watcher"
    encrypt        = true
    bucket         = "imdevinc-tf-storage"
    region         = "us-west-1"
    dynamodb_table = "terraform-state-lock-dynamo"
  }
}

locals {
  name = "wc-watcher"
}

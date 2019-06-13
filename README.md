# Slack wc-watcher
This bot uses the undocumented FIFA API's to report on World Cup matches. It will check every 60 seconds for new events. The following events are reported:
+ Goals scored
+ Yellow/Red cards
+ Substitutions
+ Match start/stop
+ Penalty kicks missed/scored

### Sample
[![sample](https://github.com/ImDevinC/wc-watcher/raw/master/assets/ss.png)](#sample)

### Usage
1. Setup a new Slack App (https://api.slack.com/apps) with Webhook permission
1. Run `build.sh` in the root to generate the necessary zip file for the lambda
1. In `terraform/variables.tf`, change the values under the **Required Variables** section as well as any other variables you may need.
1. In the `terraform` subdirectory, run `terraform apply` to create all the necessary resources
    + Lambda
    + IAM Roles
    + Dynamodb table (*this does have a small monthly cost associated with it*)
    + Cloudwatch rules

### Card emoji
1. Go to https://slack.com/customize/emoji
1. Enter `yellow_card_new` as name
1. Upload `hand_yellow_card.png`
1. Save emoji

Repeat for `red_card_new` and `hand_red_card.png`

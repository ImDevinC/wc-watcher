# Slack wc-watcher
This bot uses the undocumented FIFA API's to report on World Cup matches. It will check every 60 seconds for new events. The following events are reported:
+ Goals scored
+ Yellow/Red cards
+ Substitutions
+ Match start/stop
+ Penalty kicks missed/scored

### Usage
1. Setup a new Slack App (https://api.slack.com/apps) with Webhook permission
1. In soccerbot.py, change WEBHOOK_URL to point to your Slack webhook
1. Use `pip install -r requirements.txt`
1. Run `python soccerbot.py`

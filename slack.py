import os
import time
import re
import private
from slackclient import SlackClient
import soccerbot

RTM_READ_DELAY = 60 # Number of second delay between reading RTM
VALID_COMMANDS = []
MENTION_REGEX = '^(!\S*) +(.*)$'
BOT_ID = None
LOG_NAME = 'output.log'

def write_log(message):
    '''
        Writes the specified message to the logfile
    '''
    with open(LOG_NAME, 'a') as logfile:
        logfile.write('{}\n'.format(message))

def parse_bot_commands(slack_events):
    '''
        Parses a list of events coming from the Slack RTM API to find bot commands.
        If a bot command is found, this function returns a tuple of command and channel.
        If it's not found, then this function returns None, None.
    '''
    for event in slack_events:
        if event['type'] == 'message' and not 'subtype' in event:
            command, message = parse_direct_mention(event['text'])
            if command in VALID_COMMANDS:
                return command, message, event['channel']
    return None, None, None

def parse_direct_mention(message_text):
    '''
        Finds a direct mention (a mention that is at the beginning) in message text
        and returns the user ID which was mentioned. If there is no direct mention, returns None
    '''
    matches = re.search(MENTION_REGEX, message_text)
    if not matches:
        return None, None
    
    command = matches.group(1)
    message = matches.group(2).strip()
    
    url_matches = re.search(URL_REGEX, message)
    if url_matches:
        message = '{}{}'.format(url_matches.group(1).strip(), url_matches.group(3).strip())
    else:
        message = message.strip('<>')
    return(command, message)

def send_event(event):
    try:
        slack_client.api_call('chat.postMessage', channel='#soccerbot-test', text=event)
    except Exception as ex:
        write_log('Unable to send message: {}'.format(ex))

# def handle_command(command, message, channel):
#     '''
#         Executes bot command if the command is known
#     '''
#     # Finds and executes the given command, filling in response
#     response = None
#     # Implement commands here
#     if command == VALID_COMMANDS[0]: # Search
#         print('test')
#         # write_log('Searching for {}'.format(message))
#         # response = ipblsearch.search_for_host(message)

#     try:
#         # Send the response back
#         slack_client.api_call('chat.postMessage', channel=channel, attachments=[response])
#     except Exception as ex:
#         write_log('Unable to send message: {}'.format(ex))

if __name__ == '__main__':
    while True:
        slack_client = SlackClient(private.SLACK_TOKEN)
        if slack_client.rtm_connect(with_team_state=False):
            write_log('SoccerBot is connected and running!')
            BOT_ID = slack_client.api_call('auth.test')['user_id']
            slack_client.api_call('channels.join', channel='#soccerbot-test')
            while True:
                try:
                    events = soccerbot.check_for_updates()
                    for event in events:
                        send_event(event)
                    time.sleep(RTM_READ_DELAY)
                    # command, message, channel = parse_bot_commands(slack_client.rtm_read())
                    # if command:
                    #     handle_command(command, message, channel)
                    
                except Exception as ex:
                    write_log('Exception caught: {}'.format(ex))
                    break
        else:
            write_log('Connection failed')
"""Soccerbot scans the FIFA API for daily matches and match events.
The events are posted to a Slack channel and then stored in a dynamodb
table to prevent reposting on the next run. Once the match is over,
the dynamodb table is cleared of all events for that match.
The list of daily matches can also be retrieved.
"""
import os
import os.path
import logging
import json
from enum import Enum
from datetime import datetime, timedelta
import requests
import boto3

logging.getLogger().setLevel(os.environ['LOG_LEVEL'].upper())

WC_COMPETITION = os.environ.get('COMPETITION', '').split(',')
CHANNEL = os.environ.get('CHANNEL', '')
BOT_NAME = os.environ.get('BOT_NAME', '')
ICON_EMOJI = os.environ.get('ICON_EMOJI', '')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', '')
DYNAMO_TABLE_NAME = os.environ['DYNAMO_TABLE_NAME']

FIFA_URL = 'https://api.fifa.com/api/v1'
NOW_URL = '/live/football/now'
# IdCompetition/IdSeason/IdStage/IdMatch
MATCH_URL = '/timelines/{}/{}/{}/{}?language=en-US'
DAILY_URL = '/calendar/matches?from={}Z&to={}Z&idCompetition={}&language=en-US'
COMPETITIONS_URL = '/competitions/{}'

FLAGS = {
    'ARG': ':flag-ar:',
    'AUS': ':flag-au:',
    'BEL': ':flag-be:',
    'BOL': ':flag-bo:',
    'BRA': ':flag-br:',
    'CAN': ':flag-ca:',
    'CHI': ':flag-cl:',
    'CHN': ':flag-cn:',
    'CMR': ':flag-cm:',
    'COL': ':flag-co:',
    'CRC': ':flag-cr:',
    'CRO': ':flag-hr:',
    'DEN': ':flag-dk:',
    'ECU': ':flag-ec:',
    'EGY': ':flag-eg:',
    'ENG': ':flag-england:',
    'ESP': ':flag-es:',
    'FRA': ':flag-fr:',
    'GER': ':flag-de:',
    'IRN': ':flag-ir:',
    'ISL': ':flag-is:',
    'ITA': ':flag-it:',
    'JAM': ':flag-jm:',
    'JPN': ':flag-jp:',
    'KOR': ':flag-kr:',
    'KSA': ':flag-sa:',
    'MAR': ':flag-ma:',
    'MEX': ':flag-mx:',
    'NED': ':flag-nl:',
    'NGA': ':flag-ng:',
    'NOR': ':flag-no:',
    'NZL': ':flag-nz:',
    'PAN': ':flag-pa:',
    'PAR': ':flag-py:',
    'PER': ':flag-pe:',
    'POL': ':flag-pl:',
    'POR': ':flag-pt:',
    'QAT': ':flag-qa:',
    'RSA': ':flag-za:',
    'RUS': ':flag-ru:',
    'SCO': ':flag-scotland:',
    'SEN': ':flag-sn:',
    'SRB': ':flag-rs:',
    'SUI': ':flag-ch:',
    'SWE': ':flag-se:',
    'THA': ':flag-th:',
    'TUN': ':flag-tn:',
    'URU': ':flag-uy:',
    'VEN': ':flag-ve:',
    'ZAF': ':flag-za:'
}


class EventType(Enum):
    GOAL_SCORED = 0
    UNKNOWN_11 = 1
    YELLOW_CARD = 2
    RED_CARD = 3
    DOUBLE_YELLOW = 4
    SUBSTITUTION = 5
    IGNORE = 6
    MATCH_START = 7
    HALF_END = 8
    BLOCKED_SHOT = 12
    FOUL_UNKNOWN = 14
    UNKNOWN_10 = 13
    OFFSIDE = 15
    CORNER_KICK = 16
    BLOCKED_SHOT_2 = 17
    FOUL = 18
    UNKNOWN_7 = 19
    UNKNOWN_5 = 20
    UNKNOWN_3 = 22
    UNKNOWN_2 = 23
    UNKNOWN_4 = 24
    MATCH_END = 26
    UNKNOWN_8 = 27
    UNKNOWN_13 = 29
    UNKNOWN_9 = 30
    CROSSBAR = 32
    CROSSBAR_2 = 33
    OWN_GOAL = 34
    HAND_BALL = 37
    FREE_KICK_GOAL = 39
    PENALTY_GOAL = 41
    FREE_KICK_CROSSBAR = 44
    UNKNOWN_12 = 51
    PENALTY_MISSED = 60
    PENALTY_MISSED_2 = 65
    UNKNOWN_6 = 71
    VAR_PENALTY = 72
    UNKNOWN = 9999

    @classmethod
    def has_value(cls, value):
        """Checks if a class contains a value, treats like an ENUM check

        Arguments:
            value {EventType} -- EventType enum to check

        Returns:
            {bool} -- Value indicating whether or not the enum exists in the class
        """
        return any(value == item.value for item in cls)


class Period(Enum):
    """Period Enumerations

    Arguments:
        Enum {Enum} -- Enumeration for easily referencing the current period of play
    """
    FIRST_PERIOD = 3
    SECOND_PERIOD = 5
    FIRST_EXTRA = 7
    SECOND_EXTRA = 9
    PENALTY_SHOOTOUT = 11


def get_daily_matches(competition_id):
    """Gets a list of daily matches for the provided competition

    Arguments:
        competition_id {int} -- The ID of the competition from the FIFA API

    Returns:
        {string} -- Description of the daily matches for the competition
    """
    daily_matches = ''

    try:
        match_info_url = FIFA_URL + COMPETITIONS_URL.format(competition_id)
        response = requests.get(match_info_url)
        response.raise_for_status()
    except requests.exceptions.HTTPError as ex:
        logging.error('Failed to get competition info. %s', ex)
        return daily_matches

    competition_name = ''
    if response.json() and response.json()['Name']:
        competition_name = response.json()['Name'][0]['Description']

    now = datetime.utcnow()
    start_time = now.strftime("%Y-%m-%dT%H:00:00")
    now = now + timedelta(days=1)
    end_time = now.strftime("%Y-%m-%dT%H:00:00")
    try:
        daily_url = FIFA_URL + \
            DAILY_URL.format(start_time, end_time, competition_id)
        response = requests.get(daily_url)
        response.raise_for_status()
    except requests.exceptions.HTTPError as ex:
        logging.error('Failed to get list of daily matches.\n%s', ex)
        return daily_matches

    if response.json()['Results']:
        daily_matches = '*Todays Matches for {}:*\n'.format(competition_name)
    for match in response.json()['Results']:
        home_team = match['Home']
        home_team_id = home_team['IdCountry']
        home_team_flag = ''
        if home_team_id in FLAGS.keys():
            home_team_flag = FLAGS[home_team_id]
        away_team = match['Away']
        away_team_flag = ''
        away_team_id = away_team['IdCountry']
        if away_team_id in FLAGS.keys():
            away_team_flag = FLAGS[away_team_id]
        daily_matches += '{} {} vs {} {}\n'.format(
            home_team_flag, home_team['TeamName'][0]['Description'],
            away_team['TeamName'][0]['Description'], away_team_flag)
    return daily_matches


def get_current_matches():
    """Gets a list of all matches currently happening.
    Will filter them based on WC_COMPETITION if any values
    are present, otherwise it will look at all competitions.

    Returns:
        [{match}], [{player}] -- [description]
    """
    matches = []
    players = {}
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.get(url=FIFA_URL + NOW_URL, headers=headers)
        response.raise_for_status()
    except requests.exceptions.HTTPError as ex:
        logging.error(ex)
        return matches, players

    for match in response.json()['Results']:
        id_competition = match['IdCompetition']
        if WC_COMPETITION and id_competition not in WC_COMPETITION:
            continue
        id_season = match['IdSeason']
        id_stage = match['IdStage']
        id_match = match['IdMatch']
        home_team_id = match['HomeTeam']['IdTeam']
        for entry in match['HomeTeam']['TeamName']:
            home_team_name = entry['Description']
        away_team_id = match['AwayTeam']['IdTeam']
        for entry in match['AwayTeam']['TeamName']:
            away_team_name = entry['Description']
        if not id_competition or not id_season or not id_stage or not id_match:
            logging.warning('Invalid match information: %s', match)
            continue

        matches.append({
            'idCompetition': id_competition,
            'idSeason': id_season,
            'idStage': id_stage,
            'idMatch': id_match,
            'homeTeamId': home_team_id,
            'homeTeam': home_team_name,
            'awayTeamId': away_team_id,
            'awayTeam': away_team_name,
            'events': []
        })

        for player in match['HomeTeam']['Players']:
            player_id = player['IdPlayer']
            for player_details in player['ShortName']:
                player_name = player_details['Description']
            players[player_id] = player_name

        for player in match['AwayTeam']['Players']:
            player_id = player['IdPlayer']
            for player_details in player['ShortName']:
                player_name = player_details['Description']
            players[player_id] = player_name

    return matches, players


def get_match_events(competition_id, season_id, stage_id, match_id):
    """Gets the events for the specified match

    Arguments:
        competition_id {int} -- The competition that the match is in
        season_id {[type]} -- The season that the match is in
        stage_id {[type]} -- The stage that the match is in
        match_id {[type]} -- The match ID

    Returns:
        [{event}] -- List of events for the match
    """
    events = {}
    headers = {'Content-Type': 'application/json'}
    match_url = FIFA_URL + \
        MATCH_URL.format(competition_id, season_id, stage_id, match_id)
    try:
        response = requests.get(match_url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.HTTPError as ex:
        logging.error(ex)
        return events
    for event in response.json()['Event']:
        event_id = event['EventId']
        new_event = {}
        new_event['type'] = event['Type']
        new_event['team'] = event['IdTeam']
        new_event['player'] = event['IdPlayer']
        new_event['time'] = event['MatchMinute']
        new_event['home_goal'] = event['HomeGoals']
        new_event['away_goal'] = event['AwayGoals']
        new_event['sub'] = event['IdSubPlayer']
        new_event['period'] = event['Period']
        new_event['home_pgoals'] = event['HomePenaltyGoals']
        new_event['away_pgoals'] = event['AwayPenaltyGoals']
        new_event['url'] = match_url
        events[event_id] = new_event
    return events


def build_event(player_list, current_match, event):
    """Formats the event into a Slack message

    Arguments:
        player_list [{player}] -- List of player info
        current_match {match} -- Match information
        event {event} -- Event information

    Returns:
        {string} -- Slack message
    """
    event_message = ''
    player = player_list.get(event['player'])
    sub_player = player_list.get(event['sub'])
    active_team = current_match['homeTeam'] if event['team'] == current_match['homeTeamId'] else current_match['awayTeam']
    extra_info = False
    if (event['type'] == EventType.GOAL_SCORED.value
            or event['type'] == EventType.FREE_KICK_GOAL.value
            or event['type'] == EventType.FREE_KICK_GOAL.value):
        event_message = ':soccer: {} GOOOOAL! {} *{}:{}* {}'.format(
            event['time'], current_match['homeTeam'], event['home_goal'],
            event['away_goal'], current_match['awayTeam'])
        extra_info = True
    elif event['type'] == EventType.YELLOW_CARD.value:
        event_message = ':yellow_card_new: {} Yellow card.'.format(
            event['time'])
        extra_info = True
    elif event['type'] == EventType.RED_CARD.value:
        event_message = ':red_card_new: {} Red card.'.format(event['time'])
        extra_info = True
    elif event['type'] == EventType.DOUBLE_YELLOW.value:
        event_message = ':yellow_card_new: :red_card_new: {} Second yellow card.'.format(
            event['time'])
        extra_info = True
    elif event['type'] == EventType.SUBSTITUTION.value:
        event_message = ':arrows_counterclockwise: {} Substitution for {}.'.format(
            event['time'], active_team)
        if player and sub_player:
            event_message += '\n> {} comes on for {}.'.format(
                player, sub_player)
    elif event['type'] == EventType.MATCH_START.value:
        period = None
        if event['period'] == Period.FIRST_PERIOD.value:
            event_message = ':clock12: The match between {} and {} has begun!'.format(
                current_match['homeTeam'], current_match['awayTeam'])
        elif event['period'] == Period.SECOND_PERIOD.value:
            event_message = ':clock12: The second half of the match between {} and {} has begun!'.format(
                current_match['homeTeam'], current_match['awayTeam'])
        elif event['period'] == Period.PENALTY_SHOOTOUT.value:
            event_message = ':clock12: The penalty shootout is starting between {} and {}!'.format(
                current_match['homeTeam'], current_match['awayTeam'])
        elif event['period'] == Period.FIRST_EXTRA.value:
            event_message = ':clock12: The first half of extra time is starting between {} and {}!'.format(
                current_match['homeTeam'], current_match['awayTeam'])
        elif event['period'] == Period.SECOND_EXTRA.value:
            event_message = ':clock12: The second half of extra time is starting between {} and {}!'.format(
                current_match['homeTeam'], current_match['awayTeam'])
        else:
            event_message = ':clock12: The match between {} and {} is starting again!'.format(
                current_match['homeTeam'], current_match['awayTeam'])
    elif event['type'] == EventType.HALF_END.value:
        period = None
        if event['period'] == Period.FIRST_PERIOD.value:
            period = 'first'
        elif event['period'] == Period.SECOND_PERIOD.value:
            period = 'second'
        elif event['period'] == Period.PENALTY_SHOOTOUT.value:
            event_message = ':clock1230: The penalty shootout is over.'
        elif event['period'] == Period.FIRST_EXTRA.value:
            period = 'first extra'
        elif event['period'] == Period.SECOND_EXTRA.value:
            period = 'second extra'
        else:
            period = 'invalid'
            event_message = ':clock1230: End of the half. {} *{}:{}* {}.'.format(
                current_match['homeTeam'], event['home_goal'], event['away_goal'], current_match['awayTeam'])
        if period is not None:
            event_message = ':clock1230: End of the {} half. {} *{}:{}* {}.'.format(
                period, current_match['homeTeam'], event['home_goal'], event['away_goal'], current_match['awayTeam'])
    elif event['type'] == EventType.MATCH_END.value:
        event_message = ':clock12: The match between {} and {} has ended. {} *{}:{}* {}.'.format(current_match['homeTeam'], current_match['awayTeam'],
                                                                                                 current_match['homeTeam'], event['home_goal'], event['away_goal'], current_match['awayTeam'])
    elif event['type'] == EventType.OWN_GOAL.value:
        event_message = ':soccer: {} Own Goal! {} *{}:{}* {}'.format(
            event['time'], current_match['homeTeam'], event['home_goal'], event['away_goal'], current_match['awayTeam'])
        extra_info = True
    elif event['type'] == EventType.PENALTY_GOAL.value:
        if event['period'] == Period.PENALTY_SHOOTOUT.value:
            event_message = ':soccer: Penalty goal! {} *{} ({}):{} ({})* {}'.format(
                current_match['homeTeam'], event['home_goal'], event['home_pgoals'], event['away_goal'], event['away_pgoals'], current_match['awayTeam'])
        else:
            event_message = ':soccer: {} Penalty goal! {} *{}:{}* {}'.format(
                event['time'], current_match['homeTeam'], event['home_goal'], event['away_goal'], current_match['awayTeam'])
        extra_info = True
    elif event['type'] == EventType.PENALTY_MISSED.value or event['type'] == EventType.PENALTY_MISSED_2.value:
        if event['period'] == Period.PENALTY_SHOOTOUT.value:
            event_message = ':no_entry_sign: Penalty missed! {} *{} ({}):{} ({})* {}'.format(
                current_match['homeTeam'], event['home_goal'], event['home_pgoals'], event['away_goal'], event['away_pgoals'], current_match['awayTeam'])
        else:
            event_message = ':no_entry_sign: {} Penalty missed!'.format(
                event['time'])
        extra_info = True
    elif EventType.has_value(event['type']):
        event_message = None
    else:
        event_message = None

    if extra_info:
        if player and active_team:
            event_message += '\n> {} ({})'.format(player, active_team)
        elif active_team:
            event_message += '\n> {}'.format(active_team)

    if event_message:
        logging.debug('Sending event: %s', event_message)
        return {'message': event_message}

    return None


def save_matches(event_list):
    """Saves the event information to dynamodb

    Arguments:
        event_list [{event_info}] -- List of events to save
    """
    items = []
    for event in event_list:
        items.append({
            'PutRequest': {
                'Item': {
                    'match_id': {'N': event['match']},
                    'event_id': {'N': event['event']},
                    'event_type': {'N': str(event['type'])},
                    'stage': {'N': event['stage']},
                    'season': {'N': event['season']},
                    'competition': {'N': event['competition']},
                    'homeTeamId': {'N': event['homeTeamId']},
                    'homeTeam': {'S': event['homeTeam']},
                    'awayTeamId': {'N': event['awayTeamId']},
                    'awayTeam': {'S': event['awayTeam']}
                }
            }
        })

    client = boto3.client('dynamodb')
    while items:
        submissions = items[0:25]
        client.batch_write_item(RequestItems={DYNAMO_TABLE_NAME: submissions})
        items = items[len(submissions):]


def check_for_existing_events(match, event_list):
    """Gets a list of existing events from dynamodb for the specified match.
    Will filter out duplicate events from the input list and only return
    new events.

    Arguments:
        match {match} -- Match information
        event_list {event} -- Event information

    Returns:
        [{event_list}] -- List of new events
    """
    client = boto3.client('dynamodb')
    query_response = client.query(
        TableName=DYNAMO_TABLE_NAME,
        ExpressionAttributeValues={
            ':match_id': {
                'N': match
            }
        },
        KeyConditionExpression='match_id = :match_id'
    )
    items = query_response.get('Items')
    for event in items:
        event_id = event['event_id']['N']
        event_type_match = 'event_type' not in event or event['event_type']['N'] == event_list[event_id]
        if event_id in event_list and event_type_match:
            #event_list.pop(event['event_id']['N'])
            del event_list[event_id]

    return event_list


def get_missing_matches(live_matches):
    """Finds a list of matches in dynamodb that are not listed
    in the provided list of matches

    Arguments:
        live_matches [{int}] -- A list of match IDs

    Returns:
        [{match}] -- List of missing matches
    """
    return_matches = []
    client = boto3.client('dynamodb')
    query_response = client.scan(
        TableName=DYNAMO_TABLE_NAME,
        Select='SPECIFIC_ATTRIBUTES',
        ProjectionExpression='match_id, competition, season, stage, awayTeam, awayTeamId, homeTeam, homeTeamId'
    )
    items = query_response.get('Items')
    return_matches = [
        {'idMatch': m['match_id']['N'], 'idCompetition': m['competition']
         ['N'], 'idSeason': m['season']['N'], 'idStage': m['stage']['N'],
         'homeTeamId': m['homeTeamId']['N'], 'homeTeam': m['homeTeam']['S'],
         'awayTeamId': m['awayTeamId']['N'], 'awayTeam': m['awayTeam']['S']}
        for m in items if not m['match_id']['N'] in live_matches]
    return_matches = [dict(t)
                      for t in {tuple(d.items()) for d in return_matches}]
    return return_matches


def delete_match_events(match_id):
    """Deletes matches from dynamodb

    Arguments:
        match_id {int} -- The match_id to lookup and delete
    """
    client = boto3.client('dynamodb')
    query_response = client.query(
        TableName=DYNAMO_TABLE_NAME,
        ExpressionAttributeValues={
            ':match_id': {
                'N': match_id
            }
        },
        KeyConditionExpression='match_id = :match_id'
    )
    items = query_response.get('Items')
    delete_queue = []
    for item in items:
        delete_queue.append({
            'DeleteRequest': {
                'Key': {
                    'match_id': {'N': match_id},
                    'event_id': {'N': item['event_id']['N']}
                }
            }
        })

    while delete_queue:
        submissions = delete_queue[0:25]
        client.batch_write_item(RequestItems={DYNAMO_TABLE_NAME: submissions})
        delete_queue = delete_queue[len(submissions):]


def check_for_updates():
    """Looks for events in ongoing matches and returns a list of new events
    only.

    Returns:
        [{events}] -- List of events to send to Slack
    """
    live_matches, players = get_current_matches()
    existing_match_ids = [m['idMatch'] for m in live_matches]
    missing_matches = get_missing_matches(existing_match_ids)
    live_matches.extend(missing_matches)

    player_list = {}
    for player in players:
        if not player in player_list:
            player_list[player] = players[player]

    save_events = []
    return_events = []
    done_matches = []
    for match in live_matches:
        current_match = [
            m for m in live_matches if m['idMatch'] == match['idMatch']][0]
        event_list = get_match_events(
            match['idCompetition'], match['idSeason'], match['idStage'], match['idMatch'])
        event_list = check_for_existing_events(match['idMatch'], event_list)
        for event in event_list:
            event_notification = build_event(
                player_list, current_match, event_list[event])
            if not event_notification is None:
                return_events.append(event_notification)
            if event_list[event]['type'] == EventType.MATCH_END.value:
                done_matches.append(match['idMatch'])
                save_events = [
                    e for e in save_events if e['match'] not in done_matches]
            elif not match['idMatch'] in done_matches:
                save_events.append({
                    'event': event,
                    'type': event_list[event]['type'],
                    'match': match['idMatch'],
                    'competition': match['idCompetition'],
                    'season': match['idSeason'],
                    'stage': match['idStage'],
                    'homeTeamId': match['homeTeamId'],
                    'homeTeam': match['homeTeam'],
                    'awayTeamId': match['awayTeamId'],
                    'awayTeam': match['awayTeam']
                })

    for match_id in done_matches:
        delete_match_events(match_id)

    save_matches(save_events)
    return return_events


def send_event(event):
    """Sends a message to Slack

    Arguments:
        event {string} -- The message to send to Slack
    """
    headers = {'Content-Type': 'application/json'}
    payload = {'text': event}

    if CHANNEL:
        payload['channel'] = CHANNEL

    if BOT_NAME:
        payload['username'] = BOT_NAME

    if ICON_EMOJI:
        payload['icon_emoji'] = ICON_EMOJI

    try:
        response = requests.post(
            WEBHOOK_URL, data=json.dumps(payload), headers=headers)
        response.raise_for_status()
    except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError) as ex:
        logging.error('Failed to send message. %s', ex)


def main(event, __):
    """Primary lambda function that handles incoming requests

    Arguments:
        event {event} -- Lambda event
        __ {context} -- Lambda context (unused)
    """
    if event['type'] == 'daily_matches':
        for competition in WC_COMPETITION:
            matches = get_daily_matches(competition)
            send_event(matches)
    elif event['type'] == 'updates':
        events = check_for_updates()
        for match_event in events:
            send_event(match_event['message'])


if __name__ == '__main__':
    main({'type': 'updates'}, None)
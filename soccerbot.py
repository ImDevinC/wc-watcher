import requests
import json
import os.path
from enum import Enum
import time
import private
import asyncio
from concurrent.futures import ProcessPoolExecutor

WC_COMPETITION = None # 17 for only WC matches

FIFA_URL = 'https://api.fifa.com/api/v1'
NOW_URL = '/live/football/now'
MATCH_URL = '/timelines/{}/{}/{}/{}?language=en-US' # IdCompetition/IdSeason/IdStage/IdMatch
PLAYER_URL = ''
TEAM_URL = ''

class EventType(Enum):
    GOAL_SCORED = 0
    YELLOW_CARD = 2
    RED_CARD = 3
    DOUBLE_YELLOW = 4
    SUBSTITUTION = 5
    IGNORE = 6
    MATCH_START = 7
    HALF_END = 8
    BLOCKED_SHOT = 12
    FOUL_UNKNOWN = 14
    OFFSIDE = 15
    CORNER_KICK = 16
    BLOCKED_SHOT_2 = 17
    FOUL = 18
    UNKNOWN_3 = 22
    UNKNOWN_2 = 23
    MATCH_END = 26
    CROSSBAR = 32
    CROSSBAR_2 = 33
    OWN_GOAL = 34
    FREE_KICK_GOAL = 39
    PENALTY_GOAL = 41
    PENALTY_MISSED = 60
    UNKNOWN = 9999

    @classmethod
    def has_value(cls, value):
        return any(value == item.value for item in cls)

class Period(Enum):
    FIRST_PERIOD = 3
    SECOND_PERIOD = 5
    PENALTY_SHOOTOUT = 11

def get_current_matches():
    matches = []
    players = {}
    headers = {'Content-Type': 'application/json'}
    try:
        r = requests.get(url=FIFA_URL + NOW_URL, headers=headers)
        r.raise_for_status()
    except requests.exceptions.HTTPError as ex:
        return matches, players

    for match in r.json()['Results']:
        id_competition = match['IdCompetition']
        if WC_COMPETITION and WC_COMPETITION != id_competition:
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
            print('Invalid match information')
            continue

        matches.append({'idCompetition': id_competition, 'idSeason': id_season, 'idStage': id_stage, 'idMatch': id_match, 'homeTeamId': home_team_id, 
        'homeTeam': home_team_name, 'awayTeamId': away_team_id, 'awayTeam': away_team_name, 'events': []})

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

def get_match_events(idCompetition, idSeason, idStage, idMatch):
    events = {}
    headers = {'Content-Type': 'application/json'}
    match_url = FIFA_URL + MATCH_URL.format(idCompetition, idSeason, idStage, idMatch)
    try:
        r = requests.get(match_url, headers=headers)
        r.raise_for_status()
    except requests.exceptions.HTTPError as ex:
        return events
    for event in r.json()['Event']:
        eId = event['EventId']
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
        events[eId] = new_event
    return events

def build_event(player_list, current_match, event):
    event_message = ''
    player = player_list.get(event['player'])
    sub_player = player_list.get(event['sub'])
    active_team = current_match['homeTeam'] if event['team'] == current_match['homeTeamId'] else current_match['awayTeam']
    extraInfo = False
    if (event['type'] == EventType.GOAL_SCORED.value or event['type'] == EventType.FREE_KICK_GOAL.value
        or event['type'] == EventType.FREE_KICK_GOAL.value):
        event_message = ':soccer: {} GOOOOAL! {} *{}:{}* {}'.format(event['time'], current_match['homeTeam'], event['home_goal'], event['away_goal'], current_match['awayTeam'])
        extraInfo = True
    elif event['type'] == EventType.YELLOW_CARD.value:
        event_message = ':yellow_card_new: {} Yellow card.'.format(event['time'])
        extraInfo = True
    elif event['type'] == EventType.RED_CARD.value:
        event_message = ':red_card_new: {} Red card.'.format(event['time'])
        extraInfo = True
    elif event['type'] == EventType.DOUBLE_YELLOW.value:
        event_message = ':yellow_card_new: :red_card_new: {} Second yellow card.'.format(event['time'])
        extraInfo = True
    elif event['type'] == EventType.SUBSTITUTION.value:
        event_message = ':arrows_counterclockwise: {} Substitution for {}.'.format(event['time'], active_team)
        if player and sub_player:
            event_message += '\n> {} comes on for {}.'.format(sub_player, player)
    elif event['type'] == EventType.MATCH_START.value:
        period = None
        if event['period'] == Period.FIRST_PERIOD.value:
            event_message = ':clock12: The match between {} and {} has begun!'.format(current_match['homeTeam'], current_match['awayTeam'])
        elif event['period'] == Period.SECOND_PERIOD.value:
            event_message = ':clock12: The second half of the match between {} and {} has begun!'.format(current_match['homeTeam'], current_match['awayTeam'])
        elif event['period'] == Period.PENALTY_SHOOTOUT.value:
            event_message = ':clock12: The penalty shootout is starting between {} and {}!'.format(current_match['homeTeam'], current_match['awayTeam'])
        else:
            event_message = ':clock12: The match between {} and {} is starting again!'.format(current_match['homeTeam'], current_match['awayTeam'])
    elif event['type'] == EventType.HALF_END.value:
        period = None
        if event['period'] == Period.FIRST_PERIOD.value:
            period = 'first'
        elif event['period'] == Period.SECOND_PERIOD.value:
            period = 'second'
        elif event['period'] == Period.PENALTY_SHOOTOUT.value:
            event_message = ':clock1230: The penalty shootout is over.'
        else:
            period = 'invalid'
            event_message = ':clock1230: End of the half. {} *{}:{}* {}.'.format(current_match['homeTeam'], event['home_goal'], event['away_goal'], current_match['awayTeam'])
        if period is not None:
            event_message = ':clock1230: End of the {} half. {} *{}:{}* {}.'.format(period, current_match['homeTeam'], event['home_goal'], event['away_goal'], current_match['awayTeam'])
    elif event['type'] == EventType.MATCH_END.value:
        event_message = ':clock12: The match between {} and {} has ended. {} *{}:{}* {}.'.format(current_match['homeTeam'], current_match['awayTeam'],
        current_match['homeTeam'], event['home_goal'], event['away_goal'], current_match['awayTeam'])
    elif event['type'] == EventType.OWN_GOAL.value:
        event_message = ':soccer: {} Own Goal! {} *{}:{}* {}'.format(event['time'], current_match['homeTeam'], event['home_goal'], event['away_goal'], current_match['awayTeam'])
        extraInfo = True
    elif event['type'] == EventType.PENALTY_GOAL.value:
        if event['period'] == Period.PENALTY_SHOOTOUT.value:
            event_message = ':soccer: Penalty goal! {} *{} ({}):{} (){}* {}'.format(current_match['homeTeam'], event['home_goal'], event['home_pgoals'], event['away_goal'], event['away_pgoals'], current_match['awayTeam'])
        else:
            event_message = ':soccer: {} Penalty goal! {} *{}:{}* {}'.format(event['time'], current_match['homeTeam'], event['home_goal'], event['away_goal'], current_match['awayTeam'])
        extraInfo = True
    elif event['type'] == EventType.PENALTY_MISSED.value:
        if event['period'] == Period.PENALTY_SHOOTOUT.value:
            event_message = ':no_entry_sign: Penalty missed! {} *{} ({}):{} (){}* {}'.format(current_match['homeTeam'], event['home_goal'], event['home_pgoals'], event['away_goal'], event['away_pgoals'], current_match['awayTeam'])
        else:
            event_message = ':no_entry_sign: {} Penalty missed!'.format(event['time'])
        extraInfo = True
    elif EventType.has_value(event['type']):
        event_message = None
    elif private.DEBUG:
        event_message = 'Missing event information for {} vs {}: Event {}\n{}'.format(current_match['homeTeam'], current_match['awayTeam'], event['type'], event['url'])
    else:
        event_message = None

    if (extraInfo):
        if player and active_team:
            event_message += '\n> {} ({})'.format(player, active_team)
        elif active_team:
            event_message += '\n> {}'.format(active_team)

    return event_message

def save_matches(match_list):
    with open('match_list.txt', 'w') as file:
        file.write(json.dumps(match_list))

def load_matches():
    if not os.path.isfile('match_list.txt'):
        return {}
    with open('match_list.txt', 'r') as file:
        content = file.read()
    return json.loads(content) if content else {}
    

def check_for_updates():
    events = []
    match_list = load_matches()
    player_list = {}
    live_matches, players = get_current_matches()
    for match in live_matches:
        if not match['idMatch'] in match_list:
            match_list[match['idMatch']] = match

    for player in players:
        if not player in player_list:
            player_list[player] = players[player]

    done_matches = []
    for match in match_list:
        current_match = match_list[match]
        event_list = get_match_events(current_match['idCompetition'], current_match['idSeason'], current_match['idStage'], current_match['idMatch'])
        for event in event_list:
            if event in current_match['events']:
                continue # We already reported the event, skip it
            event_notification = build_event(player_list, current_match, event_list[event])
            current_match['events'].append(event)
            if not event_notification is None:
                events.append(event_notification)
            if event_list[event]['type'] == EventType.MATCH_END.value:
                done_matches.append(match)

    for match in done_matches:
        del match_list[match]

    save_matches(match_list)
    return events

def send_event(event, url=private.WEBHOOK_URL):
    headers = {'Content-Type': 'application/json'}
    payload = {'text': event}
    try:
        r = requests.post(url, data=json.dumps(payload), headers=headers)
        r.raise_for_status()
    except requests.exceptions.HTTPError as ex:
        print('Failed to send message: {}'.format(ex))
        return
    except requests.exceptions.ConnectionError as ex:
        print('Failed to send message: {}'.format(ex))
        return

def heart_beat():
    count = 0
    send_event('Coming up', url=private.DEBUG_WEBHOOK)
    while True:
        count = count + 1
        if count >= 60:
            count = 0
            send_event('Health ping', url=private.DEBUG_WEBHOOK)
        time.sleep(60)

def main():
    while True:
        events = check_for_updates()
        for event in events:
            send_event(event)
        time.sleep(60)

if __name__ == '__main__':
    executor = ProcessPoolExecutor(2)
    loop = asyncio.get_event_loop()
    main_task = asyncio.ensure_future(loop.run_in_executor(executor, main))
    if private.DEBUG and private.DEBUG_WEBHOOK is not '':
        heart_beat_task = asyncio.ensure_future(loop.run_in_executor(executor, heart_beat))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if main_task and not main_task.cancelled():
            main_task.cancel()
        if heart_beat_task and not heart_beat_task.cancelled():
            heart_beat_task.cancel()
        loop.close()
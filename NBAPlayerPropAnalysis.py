# -*- coding: utf-8 -*-
"""
Created on Tue Dec  3 18:29:12 2019

@author: Brandon Croarkin
"""

import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import numpy as np
import json
import psycopg2
import os
import sys
from datetime import datetime
from twilio.rest import Client
sys.path.append(os.path.dirname(os.path.abspath('config.py')) + '\\Documents\\GitHub\\SportsBetting')
import config

########################### Custom Functions ##################################

def find_between( s, first, last ):
    try:
        start = s.index( first ) + len( first )
        end = s.index( last, start )
        return s[start:end]
    except ValueError:
        return ""

def impliedOddsConverter(odds):
    """
    @odds the over or under odds. 
    Can be either positive (+105) or minus odds (-115). The goal is to convert 
    american odds into an implied probability. 
    Examples:
        1. -115 is an implied probability of 53.48%
        2. +105 is an implied probability of 48.78%
    """
    # The formula to use varies on whether it is a minus or positive odd
    if odds == 'EVEN': # even odds
        return(0.5)
    elif odds[0] == '-': # negative odds
        odds = int(odds[1:]) # convert to integer for calculations
        implied_probability = odds / (odds + 100)
        implied_probability = round(implied_probability, 2)
        return(implied_probability)
    else: # positive odds
        odds = int(odds[1:]) # convert to integer for calculations
        implied_probability = 100 / (odds +100)
        implied_probability = round(implied_probability, 2)
        return(implied_probability)

def extractNameTeamTime(bs4_item):
    """
    @bs4_item the BeautifulSoup item that contains the player name, team, 
    opponent, and gametime
    Goal of this function is to parse this string to extract all the items
    listed. 
    """
    # all the needed information is in the 5th item in this list
    data = list(bs4_item[5])
    
    # Lookup to know what field we are looking for for each list item
    item_lookup = {3: 'Player',
                   5: 'Position',
                   7: 'Team, Opponent, Time'}
    
    # Need another lookup to break out team, opponent, and time
    tot_lookup = {1: 'Team',
                  3: 'Opponent',
                  5: 'Time'}
    
    for num, item in enumerate(data):
        if num in item_lookup.keys():
            if item_lookup[num] == 'Player':
                player = list(data[3])[0].replace('\n','').lstrip().rstrip()
            elif item_lookup[num] == 'Position':
                position = list(data[5])[0]
            else:
                tot = list(data[7])
                for num, item in enumerate(tot):
                    if num in tot_lookup.keys():
                        if tot_lookup[num] == 'Team':
                            team = list(tot[1])[0].replace('\n','').lstrip().rstrip()
                        elif tot_lookup[num] == 'Opponent':
                            opponent = list(tot[3])[0].replace('\n','').lstrip().rstrip()
                        else: #Time
                            time = list(tot[5])[0].replace('\n','').lstrip().rstrip().split()[1]
                            
    return(player, position, team, opponent, time)
                            

######################## BOVADA NBA PLAYER PROPS ##############################

# Create an empty dataframe to append data to (excluding Def and K)
nba_bovada_props_comparison = pd.DataFrame(columns = ['DATE', 'PLAYER', 'TEAM', 'PROP', 'LINE', 'OVER_ODDS', 'UNDER_ODDS'])

# We are getting the stats from the current week
todays_date = datetime.now().strftime("%m/%d/%Y")

# USING THE ACTUAL API
bovada_url = 'https://www.bovada.lv/services/sports/event/v2/events/A/description/basketball/nba'
bovada_response = requests.get(bovada_url)
bovada_txt = bovada_response.text
    
# Format the json
bovada_json = json.loads(bovada_txt)
bovada_events = bovada_json[0]['events']

# Iterate over bovada_events to extract the different player props
for game in bovada_events:
    if '@' not in game['description']:
        # Bovada lists futures here, we can skip this...for now
        continue
    else:
        away_team, home_team = game['description'].split(' @ ')
        bet_groups = game['displayGroups']
        for bet_group in bet_groups:
            if bet_group['description'] == 'Player Props':
                bet_markets = bet_group['markets']
                for item in bet_markets:
                    prop_type = item['description'].split(sep = '-')[0].split(sep = '(')[0].lstrip().rstrip() if '-' in item['description'] else 'N/A'
                    if prop_type in ['Total Points', 'Total Rebounds', 'Total Points and Rebounds',
                                     'Total Rebounds and Assists', 'Total Points, Rebounds and Assists']:
                        team = item['description'].split(sep = '-')[1].split(sep = '(')[1].lstrip().rstrip().replace(')','')
                        player = item['description'].split(sep = '-')[1].split(sep = '(')[0].lstrip().rstrip()
                        prop = item['outcomes'][0]['price']['handicap']
                        over_odds = item['outcomes'][0]['price']['american']
                        under_odds = item['outcomes'][1]['price']['american']
                        # Add all these items to list
                        prop_list = [todays_date, player, team, prop_type, prop, over_odds, under_odds]
                        # Append the list to the dataframe         
                        bovada_props_comparison.loc[len(bovada_props_comparison)] = prop_list
            else:
                continue
                    
######################### NUMBER FIRE PROJECTIONS #############################

         
number_fire_url = 'https://www.numberfire.com/nba/daily-fantasy/daily-basketball-projections#_=_'

# Web scrape Fantasy Pros for relevant information
response = requests.get(number_fire_url)
soup = BeautifulSoup(response.text, "html.parser")

projections = list(list(list(list(list(list(list(list(list(soup.children)[93])[3])[5])[3])[7])[2])[1])[3])

projection_lookup = {1: 'Player',
                     3: 'FP',
                     5: 'FanDuelCost',
                     7: 'Value',
                     9: 'Min',
                     11: 'Pts',
                     13: 'Reb',
                     15: 'Ast',
                     17: 'Stl', 
                     19: 'Blk',
                     21: 'TO'}

for num, item in enumerate(projections):
    if num != 1:
        # this just to test that the loop works properly
        continue
#    if str(item) == '\n':
#        continue
    else:
        # This item contains the projecitons for a specific NBA player
        player_data = list(item)
        # Iterate over the list to extract the relevant data
        for num, item in enumerate(player_data):
            if num in projection_lookup.keys():
                if projection_lookup[num] == 'Player':
                    Player, Position, Team, Opponent, Time = extractNameTeamTime(list(player_data[num]))
                elif projection_lookup[num] == 'FP':
                    FP = list(player_data[num])[0].replace('\n','').lstrip().rstrip()
                elif projection_lookup[num] == 'FanDuelCost':
                    FanDuelCost = list(player_data[num])[0].replace('\n','').lstrip().rstrip()
                elif projection_lookup[num] == 'Value':
                    Value = list(player_data[num])[0].replace('\n','').lstrip().rstrip()
                elif projection_lookup[num] == 'Min':
                    Min = list(player_data[num])[0].replace('\n','').lstrip().rstrip()
                elif projection_lookup[num] == 'Pts':
                    Pts = list(player_data[num])[0].replace('\n','').lstrip().rstrip()
                elif projection_lookup[num] == 'Reb':
                    Reb = list(player_data[num])[0].replace('\n','').lstrip().rstrip()
                elif projection_lookup[num] == 'Ast':
                    Ast = list(player_data[num])[0].replace('\n','').lstrip().rstrip()
                elif projection_lookup[num] == 'Stl':
                    Stl = list(player_data[num])[0].replace('\n','').lstrip().rstrip()
                elif projection_lookup[num] == 'Blk':
                    Blk = list(player_data[num])[0].replace('\n','').lstrip().rstrip()
                elif projection_lookup[num] == 'TO':
                    TO = list(player_data[num])[0].replace('\n','').lstrip().rstrip()

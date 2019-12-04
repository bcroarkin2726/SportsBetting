# -*- coding: utf-8 -*-
"""
Created on Tue Dec  3 18:29:12 2019

@author: Brandon Croarkin
"""

import requests
from bs4 import BeautifulSoup

########################### Custom Functions ##################################

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
                            
###############################################################################
           
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

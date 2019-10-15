# -*- coding: utf-8 -*-
"""
Created on Wed Oct  2 11:27:37 2019

@author: Brandon Croarkin
"""

import requests
import urllib.request
import time
from bs4 import BeautifulSoup
import re
import pandas as pd
import numpy as np
import json
import psycopg2
import os
from datetime import datetime

# Set working directory to the file path of this file
abspath = os.path.abspath('PlayerPropAnalysis.py')
dname = os.path.dirname(abspath)
os.chdir(dname)

############# HELPER FUNCTIONS ######################
def find_between( s, first, last ):
    try:
        start = s.index( first ) + len( first )
        end = s.index( last, start )
        return s[start:end]
    except ValueError:
        return ""
    
def over_under(row):
    if row['BOVADA_LINE'] > row['FP_PROJECTION']:
        return('Under')
    elif row['BOVADA_LINE'] < row['FP_PROJECTION']:
        return('Over')
    else:
        return('Push')
    
def bet_scores(row):
    """
    @@row a row from the bovada_props_comparison table
    Given the difference and pct_difference between the bovada line and the 
    fp projection, we can assign grades based on how good of bets these are.
    Need to balance the weight given to difference and pct_difference since 
    this varies across values. 
    Scores will be created based on the difference and pct_difference. The 
    weight to these two factors will vary based on the bovada line. The score
    will then be used to assign a grade
    """
    difference = row['DIFFERENCE']
    pct_difference = row['PCT_DIFFERENCE']
    bovada_line = row['BOVADA_LINE']
    
    if bovada_line < 10:
        # in this extremely low category, nearly all weight should be given to pct difference
        diff_weight = .1
        pct_weight = .9
        diff_score = (difference / 20) * 50
        pct_score = 50 if pct_difference > 100 else pct_difference / 50
        score = (diff_score * diff_weight) + (pct_score * diff_weight)
        return(score)
    if bovada_line < 25:
        # in this very low category, most weight should be given to pct difference
        diff_weight = .2
        pct_weight = .8
        diff_score = (difference / 20) * 50
        pct_score = 50 if pct_difference > 100 else pct_difference / 50
        score = (diff_score * diff_weight) + (pct_score * diff_weight)
        return(score)
    elif bovada_line < 50:
        # in this low category, more weight should be given to pct difference
        diff_weight = .35
        pct_weight = .65
        diff_score = (difference / 20) * 50
        pct_score = 50 if pct_difference > 100 else pct_difference / 50
        score = (diff_score * diff_weight) + (pct_score * diff_weight)
        return(score)
    elif bovada_line < 100:
        # in this medium category, the categories should have even weights
        diff_weight = .5
        pct_weight = .5
        diff_score = (difference / 20) * 50
        pct_score = 50 if pct_difference > 100 else pct_difference / 50
        score = (diff_score * diff_weight) + (pct_score * diff_weight)
        return(score)
    elif bovada_line < 200:
        # in this high category, more weight should be given to difference
        diff_weight = .65
        pct_weight = .35
        diff_score = (difference / 20) * 50
        pct_score = 50 if pct_difference > 100 else pct_difference / 50
        score = (diff_score * diff_weight) + (pct_score * diff_weight)
        return(score)
    else:
        # in this very high category, most weight should be given to difference
        diff_weight = .8
        pct_weight = .2
        diff_score = (difference / 20) * 50
        pct_score = 50 if pct_difference > 100 else pct_difference / 50
        score = (diff_score * diff_weight) + (pct_score * pct_weight)
        return(score)

def bet_grades(row):
    score = row['BET_SCORE']
    if score > 40.0: 
        return('A+')
    elif score > 30.0:
        return('A')
    elif score > 20.0:
        return('B+')
    elif score > 15.0:
        return('B')
    elif score > 10.0:
        return('C+')
    elif score > 7.0:
        return('C')
    elif score > 5.0:
        return('D+')
    elif score > 3.0:
        return('D')
    else:
        return('F')

def findNFLWeek(Date):
   try:
        connection = psycopg2.connect(user = "postgres",
                                      password = "RfC93TiD!ab",
                                      host = "127.0.0.1",
                                      port = "5432",
                                      database = "SportsBetting")
        cursor = connection.cursor()
        # Check if row already exists
        sql_select_query = f"SELECT nfl_week FROM nflweeks WHERE currentdate = $${Date}$$"
        cursor.execute(sql_select_query)
        results = cursor.fetchone()[0]
        return(results)
   except (Exception, psycopg2.Error) as error:
       print("Error in update operation", error)
   finally:
       # closing database connection.
       if (connection):
           cursor.close()
           connection.close()

def upsertPlayerProjections(row):
    """
    @@row - row from fp_projections with projections for a player in a given nfl week
    This function will go row-by-by through fp_projections and update player projections
    for any players that are already in the table for the given nfl week and insert 
    player projections for any players that are not already in the table for the given
    nfl week. 
    """
    try:
        connection = psycopg2.connect(user = "postgres",
                                      password = "RfC93TiD!ab",
                                      host = "127.0.0.1",
                                      port = "5432",
                                      database = "SportsBetting")
        cursor = connection.cursor()
        # Check if row already exists
        nfl_week = row['NFL_WEEK']
        player = row['PLAYER']
        team = row['TEAM']
        position = row['POSITION']
        sql_select_query = f"SELECT * FROM player_projections WHERE nfl_week = {nfl_week} \
        AND player = $${player}$$ AND team = $${team}$$ AND position = $${position}$$"
        cursor.execute(sql_select_query)
        results = cursor.fetchone()
        if results:
            # If there are results that means the row is already there and should just be updated
            sql_update_query = f"UPDATE player_projections SET nfl_week = {nfl_week}, player = $${player}$$, \
                position = $${position}$$, team = $${team}$$, pass_att = {row['PASS_ATT']}, \
                cmp = {row['CMP']}, pass_yds = {row['PASS_YDS']}, pass_tds = {row['PASS_TDS']}, \
                ints = {row['INTS']}, rush_att = {row['RUSH_ATT']}, rush_yds = {row['RUSH_YDS']}, \
                rush_tds = {row['RUSH_TDS']}, rec = {row['REC']}, rec_yds = {row['REC_YDS']}, \
                rec_tds = {row['REC_TDS']}, sack = {row['SACK']}, int = {row['INT']}, fr = {row['FR']}, \
                ff = {row['FF']}, def_td = {row['DEF_TD']}, safety = {row['SAFETY']}, pa = {row['PA']}, \
                yds_agn = {row['YDS_AGN']}, fg = {row['FG']}, fga = {row['FGA']}, xpt = {row['XPT']}, \
                fpts = {row['FPTS']} WHERE nfl_week = {nfl_week} AND player = $${player}$$ AND \
                team = $${team}$$ AND position = $${position}$$"
            cursor.execute(sql_update_query)
            connection.commit()
        else:
            # Insert single record
            sql_insert_query = f"INSERT INTO player_projections (nfl_week, player, position, team, pass_att, \
            cmp, pass_yds, pass_tds, ints, rush_att, rush_yds, rush_tds, rec, rec_yds, rec_tds, sack, int, fr, ff, def_td, \
            safety, pa, yds_agn, fg, fga, xpt, fpts) \
            VALUES ({nfl_week}, $${player}$$, $${position}$$, $${team}$$, {row['PASS_ATT']}, {row['CMP']}, \
            {row['PASS_YDS']}, {row['PASS_TDS']}, {row['INTS']}, {row['RUSH_ATT']}, {row['RUSH_YDS']}, \
            {row['RUSH_TDS']}, {row['REC']}, {row['REC_YDS']}, {row['REC_TDS']}, {row['SACK']}, {row['INT']}, \
            {row['FR']}, {row['FF']}, {row['DEF_TD']}, {row['SAFETY']}, {row['PA']}, {row['YDS_AGN']}, \
            {row['FG']}, {row['FGA']}, {row['XPT']}, {row['FPTS']})"
            cursor.execute(sql_insert_query)
            connection.commit()
    except (Exception, psycopg2.Error) as error:
       print("Error in operation", error)
    finally:
       # closing database connection.
       if (connection):
           cursor.close()
           connection.close()

########################### ESPN API ####################
league_id = 28265348
year = 2019
url = "https://fantasy.espn.com/apis/v3/games/ffl/leagueHistory/" + \
      str(league_id) + "?seasonId=" + str(year)

r = requests.get(url)
d = r.json()[0]

##################### BOVADA PLAYER PROPS ################################

# Create an empty dataframe to append data to (excluding Def and K)
bovada_props_comparison = pd.DataFrame(columns = ['PLAYER', 'TEAM', 'PROP', 'BOVADA_LINE', 'FP_PROJECTION'])

# using a text file of the Bovada api results as a test since the player props
# only update on Sunday, Monday, and Thursday morning
bovada_url = 'https://www.bovada.lv/services/sports/event/v2/events/A/description/football/nfl'
bovada_response = requests.get(bovada_url)
bovada_txt = bovada_response.text
bovada_json = json.loads(bovada_txt)
bovada_events = bovada_json[0]['events']
for game in bovada_events:
    away_team, home_team = game['description'].split(' @ ')
    game_props = game['displayGroups']
    for value in game_props:
        prop_type = value['description']
        bet_markets = value['markets']
        if prop_type in ['Receiving Props', 'Rushing Props', 'Quarterback Props']:
            for player_prop in bet_markets:
                player = find_between( player_prop['description'], ' - ', '(').lstrip().rstrip()
                prop = player_prop['description'].split('-')[0].rstrip()
                try:
                    line = player_prop['outcomes'][0]['price']['handicap']
                except IndexError:
                    continue
                team = find_between(player_prop['id'],'(', ')')
                prop_list = [player, team, prop, line, '']
                # Append the list to the dataframe         
                bovada_props_comparison.loc[len(bovada_props_comparison)] = prop_list

##################### FANTASY PROS PROJECTIONS ###########################

### 1. Create fantasy projections in one table for QB, RB, WR, and TE

# Create lookup for the stat columns we are collecting
stats_lookup = {'QB': {1: 'PASS_ATT', 2: 'CMP', 3: 'PASS_YDS', 4: 'PASS_TDS',
             5: 'INTS', 6: 'RUSH_ATT', 7: 'RUSH_YDS', 8: 'RUSH_TDS', 10: 'FPTS'},
    'RB': {1: 'RUSH_ATT', 2: 'RUSH_YDS', 3: 'RUSH_TDS', 4: 'REC', 5: 'REC_YDS',
             6: 'REC_TDS', 8: 'FPTS'}, 
    'WR': {1: 'REC', 2: 'REC_YDS', 3: 'REC_TDS', 4: 'RUSH_ATT', 5: 'RUSH_YDS',
             6: 'RUSH_TDS', 8: 'FPTS'}, 
    'TE': {1: 'REC', 2: 'REC_YDS', 3: 'REC_TDS', 5: 'FPTS'},
    'DST': {1: 'SACK', 2: 'INT', 3: 'FR', 4: 'FF', 5: 'DEF_TD', 6: 'SAFETY',
             7: 'PA', 8: 'YDS_AGN', 9: 'FPTS'},
    'K': {1: 'FG', 2: 'FGA', 3: 'XPT', 4: 'FPTS'}}

# Need to make an additional dictionary for the index of FPTS of each position
position_fpts_index = {'QB': 10, 'RB': 8, 'WR': 8,
                                'TE': 5, 'DST': 9, 'K': 4}

# Create a lookup between a full team name and the abbreviation
team_abrv_lookup = {'New England Patriots': 'NE',
                    'Washington Redskins': 'WAS',
                    'Dallas Cowboys': 'DAL',
                    'Baltimore Ravens': 'BAL',
                    'Kansas City Chiefs': 'KC',
                    'Los Angeles Chargers': 'LAC', 
                    'Carolina Panthers': 'CAR',
                    'Denver Broncos': 'DEN',
                    'Atlanta Falcons': 'ATL',
                    'Tennessee Titans': 'TEN',
                    'Minnesota Vikings': 'MIN',
                    'Los Angeles Rams': 'LAR',
                    'Tampa Bay Buccaneers': 'TB',
                    'Green Bay Packers': 'GB',
                    'Seattle Seahawks': 'SEA',
                    'New Orleans Saints': 'NO',
                    'Arizona Cardinals': 'ARI',
                    'Miami Dolphins': 'MIA',
                    'San Francisco 49ers': 'SF',
                    'Cleveland Browns': 'CLE',
                    'Pittsburgh Steelers': 'PIT',
                    'Philadelphia Eagles': 'PHI',
                    'Jacksonville Jaguars': 'JAX',
                    'Detroit Lions': 'DET',
                    'New York Jets': 'NYJ',
                    'Cincinnati Bengals': 'CIN',
                    'Houston Texans': 'HOU',
                    'New York Giants': 'NYG'}

# A dictionary of the URLs to hit for each position
fantasy_pros_projection_urls = {'QB': 'https://www.fantasypros.com/nfl/projections/qb.php',
                                'RB': 'https://www.fantasypros.com/nfl/projections/rb.php?scoring=HALF',
                                'WR': 'https://www.fantasypros.com/nfl/projections/wr.php?scoring=HALF',
                                'TE': 'https://www.fantasypros.com/nfl/projections/te.php?scoring=HALF',
                                'DST': 'https://www.fantasypros.com/nfl/projections/dst.php',
                                'K': 'https://www.fantasypros.com/nfl/projections/k.php'}

# To add to the dataframe we'll need a consistent format of the lists
projection_format = {'NFL_WEEK': 0, 'PLAYER': 1, 'POSITION': 2, 'TEAM': 3, 'PASS_ATT': 4, 
                     'CMP': 5, 'PASS_YDS': 6, 'PASS_TDS': 7, 'INTS': 8, 'RUSH_ATT': 9,
                     'RUSH_YDS': 10, 'RUSH_TDS': 11, 'REC': 12, 'REC_YDS': 13, 'REC_TDS': 14,
                     'SACK': 15, 'INT': 16, 'FR': 17, 'FF': 18, 'DEF_TD': 19, 'SAFETY': 20,
                     'PA': 21, 'YDS_AGN': 22, 'FG': 23, 'FGA': 24, 'XPT': 25, 'FPTS': 26}

# Create an empty dataframe to append data to (excluding Def and K)
fp_projections = pd.DataFrame(columns = ['NFL_WEEK', 'PLAYER', 'POSITION', 'TEAM', 'PASS_ATT', 
                                         'CMP', 'PASS_YDS', 'PASS_TDS', 'INTS', 
                                         'RUSH_ATT', 'RUSH_YDS', 'RUSH_TDS', 'REC', 
                                         'REC_YDS', 'REC_TDS', 'SACK', 'INT',
                                         'FR', 'FF', 'DEF_TD', 'SAFETY', 'PA',
                                         'YDS_AGN', 'FG', 'FGA', 'XPT', 'FPTS'])

# Iterate over dictionary of URLs to add data to dictionary
for key, url in fantasy_pros_projection_urls.items():  
    # Get the position from the key
    position = key
    # Get the stat keys lookup for position
    lookup = stats_lookup[position]
    # Lookup the fpts index 
    fpts_index = position_fpts_index[position]
    # Create an empty list to update the data for
    player_projections = [0] * 27
    # Web scrape Fantasy Pros for relevant information
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    projections = list(list(list(list(list(list(list(soup.children)[25].children)[1])[1])[1])[11])[1])[3]
    projections_list =  list(projections)
    nfl_week = int(find_between(str(list(list(list(soup.children)[2])[1])[1]), 'Week ', ' ' + position))
    for num, item in enumerate(projections_list):
        if item != '\n':
            # Add the NFL Week to the list
            player_projections[0] = nfl_week
            proj_list = list(item)
            # filter out the '\n'
            proj_list = [x for x in proj_list if x != '\n']
            # Extract the player name
            player_name = str(proj_list[0]).split("fp-player-name=")[1]
            start, stop = [m.start() for m in re.finditer('"', player_name)][0:2]
            player_name = player_name[start+1:stop]
            player_projections[1] = player_name
            # Add the position to the list
            player_projections[2] = position
            # Extract the team of the player
            team = list(proj_list[0])[1].strip() if key != 'DST' else team_abrv_lookup[find_between(str(list(proj_list[0])[0]), '>', '<')]
            player_projections[3] = team
            for i, stat in enumerate(proj_list):
                if i in lookup.keys():
                    if i != fpts_index:
                        # For default format of stat results
                        stat_name = lookup[i] # get the stat name from lookup
                        list_index = projection_format[stat_name] # get the list index for this stat
                        result = re.search('<td class="center">(.*)</td>', str(stat))
                        stat_result = float(result.group(1))
                        player_projections[list_index] = stat_result
                    else:
                        # There is a different output for fantasy points
                        stat_name = lookup[i] # get the stat name from lookup
                        list_index = projection_format[stat_name] # get the list index for this stat
                        result = re.search('<td class="center" data-sort-value="(.*)">(.*)</td>', str(stat))
                        stat_result = float(result.group(2))
                        player_projections[list_index] = stat_result
                else:
                    continue
            # Append the list to the dataframe         
            fp_projections.loc[len(fp_projections)] = player_projections

# Remove rows where fpts is 0, since there are not needed
fp_projections = fp_projections[fp_projections['FPTS'] != 0.0]

# Upload the fantasy pros player projections to a postgres table
for index, row in fp_projections.iterrows():
    upsertPlayerProjections(row)
#    print(row['PLAYER'] + "'s player projections have been added.")

############### APPEND FP PROJECTIONS TO BOVADA PLAYER PROPS ##################
prop_lookups = {'Total Receiving Yards': 'REC_YDS',
               'Total Receptions': 'REC',
               'Total Passing Yards': 'PASS_YDS',
               'Total Passing Attempts in the game': 'PASS_ATT',
               'Total Touchdown Passes': 'PASS_TDS',
               'Total Completions': 'CMP',
               'Total Interceptions Thrown': 'INTS',
               'Total Rushing Yards': 'RUSH_YDS',
               'Total Rushing and Receiving Yards': ['RUSH_YDS', 'REC_YDS'],
               'Longest Reception': 'N/A',
               'Longest Completion': 'N/A'}

# Iterate over bovada_props_comparison and add in fp projections where applicable
for index, row in bovada_props_comparison.iterrows():
    player = row['PLAYER']
    bovada_line = row['BOVADA_LINE']
    prop = row['PROP']
    prop_lookup = prop_lookups[prop]
    fp_projection = fp_projections[fp_projections['PLAYER'] == player][prop_lookup].values[0] if prop_lookup != 'N/A' else 0
    fp_projection = fp_projection if type(fp_projection) in [int, float, np.float64] else round(fp_projection[0] + fp_projection[1],1)
    # append the fp_projection to the bovada table
    bovada_props_comparison.loc[index]['FP_PROJECTION'] = fp_projection

# Remove Props from bovada_props_comparison that I don't use (Longest Completion and Longest Reception)
unused_props = ['Longest Completion', 'Longest Reception']
bovada_props_comparison = bovada_props_comparison[(bovada_props_comparison['PROP'] != unused_props[0]) & 
    (bovada_props_comparison['PROP'] != unused_props[1])]    
    
# Create bet grades for each row based on difference bt Bovada line and FP projection
bovada_props_comparison['BOVADA_LINE'] = pd.to_numeric(bovada_props_comparison['BOVADA_LINE'], errors = 'coerce') # convert to float for analysis
bovada_props_comparison['FP_PROJECTION'] = pd.to_numeric(bovada_props_comparison['FP_PROJECTION'], errors = 'coerce') # convert to float for analysis
bovada_props_comparison['DIFFERENCE'] = bovada_props_comparison['BOVADA_LINE'] - bovada_props_comparison['FP_PROJECTION']
bovada_props_comparison['DIFFERENCE'] = abs(bovada_props_comparison['DIFFERENCE'])
bovada_props_comparison['PCT_DIFFERENCE'] = abs(round((bovada_props_comparison['BOVADA_LINE']/bovada_props_comparison['FP_PROJECTION'] - 1) * 100, 2))
bovada_props_comparison['DIRECTION'] = bovada_props_comparison.apply(over_under, axis = 1)
bovada_props_comparison['BET_SCORE'] = bovada_props_comparison.apply(bet_scores, axis = 1)
bovada_props_comparison['BET_GRADE'] = bovada_props_comparison.apply(bet_grades, axis = 1)

##################### FANTASY PROS PLAYER STAT TRACKING ###########################

# 1. QB Stat Tracking

qb_url5 = 'https://www.fantasypros.com/nfl/stats/qb.php?week=5&range=week&scoring=HALF'
# Grab information from URL and format into dataframe
qb_url = 'https://www.fantasypros.com/nfl/stats/qb.php?week={week_num}&range=week&scoring=HALF'
qb_response = requests.get(qb_url5)
qb_soup = BeautifulSoup(qb_response.text, "html.parser")
qb_stats_list = list(list(list(list(list(list(list(list(qb_soup.children)[25].children)[1])[1])[1])[13])[1])[3])

# To add to the dataframe we'll need a consistent format of the lists
qb_statistics_format = {'PLAYER': 0, 'POSITION': 1, 'TEAM': 2, 'WEEK': 3, 'CMP': 4, 
                        'PASS_ATT': 5, 'PCT': 6, 'PASS_YDS': 7, 'Y/A': 8, 'PASS_TDS': 9, 
                        'INTS': 10, 'SACKS': 11, 'RUSH_ATT': 12, 'RUSH_YDS': 13, 
                        'RUSH_TDS': 14, 'FPTS': 15}

# Create an empty dataframe to append data to (excluding Def and K)
qb_statistics_df = pd.DataFrame(columns = ['PLAYER', 'POSITION', 'TEAM', 'WEEK', 'CMP', 
                                        'PASS_ATT', 'PCT', 'PASS_YDS', 'Y/A', 'PASS_TDS', 'INTS', 
                                         'SACKS', 'RUSH_ATT', 'RUSH_YDS', 'RUSH_TDS', 'FPTS'])

# Create lookup for the stat columns we are collecting
qb_stats_lookup = {1: 'CMP', 2: 'PASS_ATT', 3: 'PCT', 4: 'PASS_YDS', 5: 'Y/A',
                  6: 'PASS_TDS', 7: 'INTS', 8: 'SACKS', 9: 'RUSH_ATT', 10: 'RUSH_ATT',
                  11: 'RUSH_YDS', 12: 'RUSH_TDS', 14: 'FPTS'}

for num, item in enumerate(qb_stats_list):
    if item != '\n':
        qb_list = list(item)
        # filter out the '\n'
        qb_list = [x for x in qb_list if x != '\n']
        # Create an empty list to update the data for
        qb_statistics = [0] * 16
        # Extract the team of the player
        team = list(qb_list[0])[1].strip().replace('(','').replace(')','')
        qb_statistics[2] = team
        # Extract the player name
        player_name = str(qb_list[0]).split("fp-player-name=")[1]
        start, stop = [m.start() for m in re.finditer('"', player_name)][0:2]
        player_name = player_name[start+1:stop]
        qb_statistics[0] = player_name
        # Extract the player position
        qb_statistics[1] = 'QB'
        for i, stat in enumerate(qb_list):
            if i in qb_stats_lookup.keys():
                if i != 15:
                    # For default format of stat results
                    stat_name = qb_stats_lookup[i] # get the stat name from lookup
                    list_index = qb_statistics_format[stat_name] # get the list index for this stat
                    result = re.search('<td class="center">(.*)</td>', str(stat))
                    stat_result = float(result.group(1))
#                    print(i, stat_name, stat_result)
                    qb_statistics[list_index] = stat_result
                else:
                    # There is a different output for fantasy points
                    stat_name = qb_stats_lookup[i] # get the stat name from lookup
                    list_index = qb_statistics_format[stat_name] # get the list index for this stat
                    result = re.search('<td class="center" data-sort-value="(.*)">(.*)</td>', str(stat))
                    stat_result = float(result.group(2))
#                    print(i, stat_name, stat_result)
                    qb_statistics[list_index] = stat_result
            else:
                continue
        # Append the list to the dataframe         
        qb_statistics_df.loc[len(qb_statistics_df)] = qb_statistics















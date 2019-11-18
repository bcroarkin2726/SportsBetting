# -*- coding: utf-8 -*-
"""
Created on Mon Nov 18 16:30:01 2019

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
from datetime import datetime

# Set working directory to the file path of this file
abspath = os.path.abspath('PlayerPropEvaluation.py')
dname = os.path.dirname(abspath) + '\\Documents\\GitHub\\SportsBetting' if 'GitHub' not in abspath else os.path.dirname(abspath)
os.chdir(dname)

############# HELPER FUNCTIONS ######################
def find_between( s, first, last ):
    try:
        start = s.index( first ) + len( first )
        end = s.index( last, start )
        return s[start:end]
    except ValueError:
        return ""
    
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

def checkPlayerStatistics(nfl_week):
    """
    @@nfl_week the current nfl_week
    This function is used to see if we already have player statistics for a given
    NFL week. If we do, we do not need to insert any values. If not, we need to 
    run the insertPlayerStatistics function on each row of fp_statistics df. 
    """
    try:
        connection = psycopg2.connect(user = "postgres",
                                      password = "RfC93TiD!ab",
                                      host = "127.0.0.1",
                                      port = "5432",
                                      database = "SportsBetting")
        cursor = connection.cursor()
        # Check if row already exists
        sql_select_query = f"SELECT * FROM player_statistics WHERE nfl_week = {nfl_week}"
        cursor.execute(sql_select_query)
        results = cursor.fetchone()
        if results:
            return(True)
        else:
            return(False)
    except (Exception, psycopg2.Error) as error:
       print("Error in operation", error)
    finally:
       # closing database connection.
       if (connection):
           cursor.close()
           connection.close()

def insertPlayerStatistics(row):
    """
    @@row - row from fp_statistics with statisitcs for a player in a given nfl week
    This function will go row-by-by through fp_statistics and insert player statistics
    for all relevant players within the week. Values are assumed to be final once 
    inserted.
    """
    try:
        connection = psycopg2.connect(user = "postgres",
                                      password = "RfC93TiD!ab",
                                      host = "127.0.0.1",
                                      port = "5432",
                                      database = "SportsBetting")
        cursor = connection.cursor()
        # Insert single record
        sql_insert_query = f"INSERT INTO player_statistics (nfl_week, player, position, \
            team, pass_att, cmp, pass_pct, pass_yds, pass_yds_att, pass_tds, ints, \
            sacks, rush_att, rush_yds, rush_yds_att, lg_rush, rush_20plus, rush_tds, \
            rec, tgt, rec_yds, lg_rec, rec_20plus, rec_yds_per, rec_tds, sack, int, fr, \
            ff, def_td, safety, spc_td, fg, fga, fg_pct, lg_fg, fg_1_19, fg_20_29, \
            fg_30_39, fg_40_49, fg_50plus, xpt, xpa, pct_own, fpts) \
            VALUES ({row['NFL_WEEK']}, $${row['PLAYER']}$$, $${row['POSITION']}$$, \
            $${row['TEAM']}$$, {row['PASS_ATT']}, {row['CMP']}, {row['PASS_PCT']}, \
            {row['PASS_YDS']}, {row['PASS_YDS_ATT']}, {row['PASS_TDS']}, {row['INTS']}, \
            {row['SACKS']}, {row['RUSH_ATT']}, {row['RUSH_YDS']}, {row['RUSH_YDS_ATT']}, \
            {row['LG_RUSH']}, {row['RUSH_20PLUS']}, {row['RUSH_TDS']}, {row['REC']}, \
            {row['TGT']}, {row['REC_YDS']}, {row['LG_REC']}, {row['REC_20PLUS']}, \
            {row['REC_YDS_PER']}, {row['REC_TDS']}, {row['SACK']},  {row['INT']}, \
            {row['FR']}, {row['FF']}, {row['DEF_TD']}, {row['SAFETY']}, {row['SPC_TD']}, \
            {row['FG']}, {row['FGA']}, {row['FG_PCT']}, {row['LG_FG']}, {row['FG_1_19']}, \
            {row['FG_20_29']}, {row['FG_30_39']}, {row['FG_40_49']}, {row['FG_50PLUS']}, \
            {row['XPT']}, {row['XPA']}, {row['PCT_OWN']}, {row['FPTS']})"
        cursor.execute(sql_insert_query)
        connection.commit()
    except (Exception, psycopg2.Error) as error:
       print("Error in operation", error)
    finally:
       # closing database connection.
       if (connection):
           cursor.close()
           connection.close()

def upsertBovadaPropComparisons(row):
    """
    @@row - row from bovada_props_comparison
    This function will go row-by-by through bovada_props_comparison and update bovada
    prop comparisons for any players that are already in the table for the given nfl 
    week and insert bovada prop comparisons for any players that are not already in 
    the table for the given nfl week. 
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
        prop = row['PROP']
        sql_select_query = f"SELECT * FROM bovada_props_comparison WHERE nfl_week = {nfl_week} \
        AND player = $${player}$$ AND team = $${team}$$ AND prop = $${prop}$$"
        cursor.execute(sql_select_query)
        results = cursor.fetchone()
        if results:
            # Format certain fields to prevent error in update
            actual_stat_line = row['ACTUAL_STAT_LINE'] if row['ACTUAL_STAT_LINE'] != '' else 'NULL'
            correct = row['CORRECT'] if row['CORRECT'] != '' else 'NULL'
            # If there are results that means the row is already there and should just be updated
            sql_update_query = f"UPDATE bovada_props_comparison SET nfl_week = {nfl_week}, \
                player = $${player}$$, team = $${team}$$, prop = $${row['PROP']}$$, \
                bovada_line = {row['BOVADA_LINE']}, over_odds = $${row['OVER_ODDS']}$$, \
                implied_over_probability = $${row['IMPLIED_OVER_PROBABILITY']}$$, \
                under_odds = $${row['UNDER_ODDS']}$$, implied_under_probability = \
                $${row['IMPLIED_UNDER_PROBABILITY']}$$, fp_projection = {row['FP_PROJECTION']},\
                difference = {row['DIFFERENCE']}, pct_difference = {row['PCT_DIFFERENCE']}, \
                direction = $${row['DIRECTION']}$$, bet_score = {row['BET_SCORE']}, bet_grade =\
                $${row['BET_GRADE']}$$, actual_stat_line = $${row['ACTUAL_STAT_LINE']}$$, \
                correct = $${row['CORRECT']}$$ WHERE nfl_week = {nfl_week} AND player = \
                $${player}$$ AND team = $${team}$$"
            cursor.execute(sql_update_query)
            connection.commit()
        else:
            # Insert single record
            sql_insert_query = f"INSERT INTO bovada_props_comparison (nfl_week, player, \
            team, prop, bovada_line, over_odds, implied_over_probability, under_odds, \
            implied_under_probability, fp_projection, difference, pct_difference, \
            direction, bet_score, bet_grade, actual_stat_line, correct) \
            VALUES ({nfl_week}, $${player}$$, $${team}$$, $${row['PROP']}$$, \
            {row['BOVADA_LINE']}, $${row['OVER_ODDS']}$$, $${row['IMPLIED_OVER_PROBABILITY']}$$, \
            $${row['UNDER_ODDS']}$$, $${row['IMPLIED_UNDER_PROBABILITY']}$$, \
            {row['FP_PROJECTION']}, $${row['DIFFERENCE']}$$, {row['PCT_DIFFERENCE']}, \
            $${row['DIRECTION']}$$, {row['BET_SCORE']}, $${row['BET_GRADE']}$$, NULL, NULL)"
            cursor.execute(sql_insert_query)
            connection.commit()
    except (Exception, psycopg2.Error) as error:
       print("Error in operation", error)
    finally:
       # closing database connection.
       if (connection):
           cursor.close()
           connection.close()


        
def assessBovadaProp(row):
    """
    @@row a row from the bovada props comparison table
    The goal of this function is to look at the Bovada line and the actual value
    and determine if the bet was correct, wrong, or a push.
    """
    bovada_line = row['BOVADA_LINE']
    actual_stat_line = row['ACTUAL_STAT_LINE']
    direction = row['DIRECTION']
    # If nan, we can't determine so we'll set it to NA
    # Comparing the value to itself to check if it is nan
    if actual_stat_line != actual_stat_line:
        return(None)
    else:
        if direction == 'Push':
            # if direction is push, we aren't taking a side in the bet
            return(None)
        elif direction == 'Under':
            if bovada_line == actual_stat_line:
                # if there is no difference we push on the bet and won't count it
                return(None)
            elif bovada_line > actual_stat_line: 
                return(True)
            else: 
                return(False)
        else: # the direction is Over
            if bovada_line == actual_stat_line:
                # if there is no difference we push on the bet and won't count it
                return(None)
            elif bovada_line > actual_stat_line: 
                return(False)
            else: 
                return(True)

##################### FANTASY PROS PLAYER STAT TRACKING ###########################

# We are getting the stats from the previous week
todays_date = datetime.now().strftime("%m/%d/%Y")
nfl_week = findNFLWeek(todays_date) - 1 

# Create an empty dataframe to append data to (excluding Def and K)
fp_statistics = pd.DataFrame(columns = ['NFL_WEEK', 'PLAYER', 'POSITION', 'TEAM', 'PASS_ATT', 
                                         'CMP', 'PASS_PCT', 'PASS_YDS', 'PASS_YDS_ATT', 'PASS_TDS', 'INTS', 
                                         'SACKS', 'RUSH_ATT', 'RUSH_YDS', 'RUSH_YDS_ATT', 'LG_RUSH', 
                                         'RUSH_20PLUS', 'RUSH_TDS', 'REC', 'TGT', 'REC_YDS', 'LG_REC', 
                                         'REC_20PLUS', 'REC_YDS_PER', 'REC_TDS', 'SACK', 'INT', 'FR', 'FF', 
                                         'DEF_TD', 'SAFETY', 'SPC_TD', 'FG', 'FGA', 'FG_PCT', 
                                         'LG_FG', 'FG_1_19', 'FG_20_29', 'FG_30_39', 'FG_40_49', 'FG_50PLUS', 'XPT', 
                                         'XPA', 'PCT_OWN', 'FPTS'])

# Need to make an additional dictionary for the index of FPTS of each position
position_fpts_index = {'QB': 14, 'RB': 14, 'WR': 13, 'TE': 13, 'DST': 9, 'K': 13}

# To add to the dataframe we'll need a consistent format of the keys place in dataframe
statistics_format = {'NFL_WEEK': 0, 'PLAYER': 1, 'POSITION': 2, 'TEAM': 3, 'PASS_ATT': 4, 
                            'CMP': 5, 'PASS_PCT': 6, 'PASS_YDS': 7, 'PASS_YDS_ATT': 8, 'PASS_TDS': 9, 
                            'INTS': 10, 'SACKS': 11, 'RUSH_ATT': 12, 'RUSH_YDS': 13, 
                            'RUSH_YDS_ATT': 14, 'LG_RUSH': 15, 'RUSH_20PLUS': 16, 'RUSH_TDS': 17, 
                            'REC': 18, 'TGT': 19, 'REC_YDS': 20, 'LG_REC': 21, 'REC_20PLUS': 22,
                            'REC_YDS_PER': 23, 'REC_TDS': 24, 'SACK': 25, 'INT': 26, 'FR': 27, 
                            'FF': 28, 'DEF_TD': 29, 'SAFETY': 30, 'SPC_TD': 31, 'FG': 32, 'FGA': 33, 
                            'FG_PCT': 34, 'LG_FG': 35, 'FG_1_19': 36, 'FG_20_29': 37, 
                            'FG_30_39': 38, 'FG_40_49': 39, 'FG_50PLUS': 40, 'XPT': 41, 'XPA': 42, 
                            'PCT_OWN': 43, 'FPTS': 44}

# Create lookup for the stat columns we are collecting from fantasy pros
# The nested key is the loop index and the value is the stat it corresponds to
stats_lookup = {'QB': {1: 'CMP', 2: 'PASS_ATT', 3: 'PASS_PCT', 4: 'PASS_YDS', 5: 'PASS_YDS_ATT', 
                       6: 'PASS_TDS', 7: 'INTS', 8: 'SACKS', 9: 'RUSH_ATT', 
                       10: 'RUSH_YDS', 11: 'RUSH_TDS', 12: 'PCT_OWN', 14: 'FPTS'},
    'RB': {1: 'RUSH_ATT', 2: 'RUSH_YDS', 3: 'RUSH_YDS_ATT', 4: 'LG_RUSH', 5: 'RUSH_20PLUS',
           6: 'RUSH_TDS', 7: 'REC', 8: 'TGT', 9: 'REC_YDS', 10: 'REC_YDS_PER', 11: 'REC_TDS',
           16: 'PCT_OWN', 14: 'FPTS'},
    'WR': {1: 'REC', 2: 'TGT', 3: 'REC_YDS', 4: 'REC_YDS_PER', 5: 'LG_REC', 6: 'REC_20PLUS',
           7: 'REC_TDS', 8: 'RUSH_ATT', 9: 'RUSH_YDS', 10: 'RUSH_TDS', 
           15: 'PCT_OWN', 13: 'FPTS'},
    'TE': {1: 'REC', 2: 'TGT', 3: 'REC_YDS', 4: 'REC_YDS_PER', 5: 'LG_REC', 6: 'REC_20PLUS',
           7: 'REC_TDS', 8: 'RUSH_ATT', 9: 'RUSH_YDS', 10: 'RUSH_TDS', 
           13: 'FPTS', 15: 'PCT_OWN'},
    'K': {1: 'FG', 2: 'FGA', 3: 'FG_PCT', 4: 'LG_FG', 5: 'FG_1_19', 6: 'FG_20_29', 7: 'FG_30_39',
          8: 'FG_40_49', 9: 'FG_50PLUS', 10: 'XPT', 11: 'XPA', 13: 'FPTS', 15: 'PCT_OWN'},
    'DST': {1: 'SACK', 2: 'INT', 3: 'FR', 4: 'FF', 5: 'DEF_TD', 6: 'SAFETY',
            7: 'SPC_TD', 9: 'FPTS', 11: 'PCT_OWN'}
    }

# A dictionary with f-string of the URL to hit for each position given the position and nfl_week
fantasy_pros_statistic_urls = {'QB': f'https://www.fantasypros.com/nfl/stats/qb.php?week={nfl_week}&range=week&scoring=HALF', 
                               'RB': f'https://www.fantasypros.com/nfl/stats/rb.php?week={nfl_week}&range=week&scoring=HALF',
                               'WR': f'https://www.fantasypros.com/nfl/stats/wr.php?week={nfl_week}&range=week&scoring=HALF',
                               'TE': f'https://www.fantasypros.com/nfl/stats/te.php?week={nfl_week}&range=week&scoring=HALF',
                               'DST': f'https://www.fantasypros.com/nfl/stats/dst.php?week={nfl_week}&range=week&scoring=HALF', 
                               'K': f'https://www.fantasypros.com/nfl/stats/k.php?week={nfl_week}&range=week&scoring=HALF'}

# Iterate over dictionary of URLs to add data to dictionary
for position, url in fantasy_pros_statistic_urls.items():  
    # Get the stat keys lookup for position
    lookup = stats_lookup[position]
    # Lookup the fpts index 
    fpts_index = position_fpts_index[position]
    # Web scrape Fantasy Pros for relevant information
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    stats_list = list(list(list(list(list(list(list(list(soup.children)[25].children)[1])[1])[1])[13])[1])[3])
    for num, item in enumerate(stats_list):
        if item != '\n':
            stat_list = list(item)
            # filter out the '\n'
            stat_list = [x for x in stat_list if x != '\n']
            # Create an empty list to update the data for
            statistics = [0] * 45
            # Update the NFL Week
            statistics[0] = nfl_week
            # Update the position
            statistics[2]= position
            # Extract the team of the player
            team = list(stat_list[0])[1].strip().replace('(','').replace(')','')
            statistics[3] = team
            # Extract the player name
            player_name = str(stat_list[0]).split("fp-player-name=")[1]
            start, stop = [m.start() for m in re.finditer('"', player_name)][0:2]
            player_name = player_name[start+1:stop]
            statistics[1] = player_name
            for i, stat in enumerate(stat_list):
                if i in lookup.keys():
                    stat_name = lookup[i] # get the stat name from lookup
                    list_index = statistics_format[stat_name] # get the list index for this stat
                    result = re.search('<td class="center">(.*)</td>', str(stat))
                    if result.group(1) != '':
                        try:
                            stat_result = float(result.group(1))
                        except:
                            # for handling PCT_OWN (ex: 19.0% doesn't convert to float)
                            stat_result = float(result.group(1).replace('%',''))/100
                    else:
                        continue
                    statistics[list_index] = stat_result
                else:
                    continue
            # Append the list to the dataframe         
            fp_statistics.loc[len(fp_statistics)] = statistics

# Filter the fp_statistics table to just relevant players (either have a pass_att, rush_att, tgt, fga, or are a DST)
fp_statistics = fp_statistics[(fp_statistics['PASS_ATT'] > 0) | (fp_statistics['RUSH_ATT'] > 0) | \
                              (fp_statistics['TGT'] > 0) | (fp_statistics['FGA'] > 0) | (fp_statistics['POSITION'] == 'DST') ]

# Upload the fantasy pros player projections to a postgres table if we don't have 
# anything for the current week
if checkPlayerStatistics(nfl_week):
    # This means that we have player statistics for the week already, so we can skip
    pass
else:
    for index, row in fp_statistics.iterrows():
        insertPlayerStatistics(row)
        
################ APPEND FP STATISTICS TO BOVADA PLAYER PROPS ##################

# Read the previous week's bovada props into a dataframe
try:
    connection = psycopg2.connect(user = "postgres",
                                  password = "RfC93TiD!ab",
                                  host = "127.0.0.1",
                                  port = "5432",
                                  database = "SportsBetting")
    cursor = connection.cursor()
    sql_select_query = f"SELECT * FROM bovada_props_comparison WHERE nfl_week = {nfl_week}"
    cursor.execute(sql_select_query)
    bovada_props_comparison_previous_week = pd.DataFrame(cursor.fetchall(), 
            columns = ['NFL_WEEK', 'PLAYER', 'TEAM', 'PROP', 'BOVADA_LINE', 
                       'OVER_ODDS', 'IMPLIED_OVER_PROBABILITY', 
                       'UNDER_ODDS', 'IMPLIED_UNDER_PROBABILITY', 'FP_PROJECTION',
                       'DIFFERENCE', 'PCT_DIFFERENCE', 'DIRECTION', 'BET_SCORE',
                       'BET_GRADE', 'ACTUAL_STAT_LINE', 'CORRECT'])
except (Exception, psycopg2.Error) as error:
   print("Error in operation", error)
finally:
   # closing database connection.
   if (connection):
       cursor.close()
       connection.close()
       
# Read the previous week's fantasy stats into a dataframe
try:
    connection = psycopg2.connect(user = "postgres",
                                  password = "RfC93TiD!ab",
                                  host = "127.0.0.1",
                                  port = "5432",
                                  database = "SportsBetting")
    cursor = connection.cursor()
    sql_select_query = f"SELECT * FROM player_statistics WHERE nfl_week = {nfl_week}"
    cursor.execute(sql_select_query)
    fp_stats_prev_week = pd.DataFrame(cursor.fetchall(), 
            columns = ['NFL_WEEK', 'PLAYER', 'POSITION', 'TEAM', 'PASS_ATT',
                       'CMP', 'PASS_PCT', 'PASS_YDS', 'PASS_YDS_ATT', 'PASS_TDS', 
                       'INTS', 'SACKS', 'RUSH_ATT', 'RUSH_YDS', 'RUSH_YARDS_ATT', 
                       'LG_RUSH', 'RUSH_20plus', 'RUSH_TDS', 'REC', 'TGT', 
                       'REC_YDS', 'LG_REC', 'REC_2OPLUS', 'REC_YDS_PER', 
                       'REC_TDS', 'SACK', 'INT', 'FR', 'FF', 'DEF_TD', 'SAFETY', 
                       'SPC_TD', 'FG', 'FGA', 'FG_PCT', 'LG_FG', 'FG_1_19',
                       'FG_20_29', 'FG_30_39', 'FG_40_49', 'FG_50PLUS', 'XPT', 
                       'XPA', 'PCT_OWN', 'FPTS'])
except (Exception, psycopg2.Error) as error:
   print("Error in operation", error)
finally:
   # closing database connection.
   if (connection):
       cursor.close()
       connection.close()

# Append the fantasy statistics to the bovada props comparison
for index, row in bovada_props_comparison.iterrows():
    player = row['PLAYER']
    team = row['TEAM'] if row['TEAM'] != 'LA' else 'LAR'
    # Link the bovada prop to the fantasy statistic
    prop = row['PROP']
    fp_stat = prop_lookups[prop]
    if type(fp_stat) != list:
        # Get the value for the prop for the player during the given nfl week
        try:
            fp_stat_value = fp_stats_prev_week[(fp_stats_prev_week['PLAYER'] == player) \
                                    & (fp_stats_prev_week['TEAM'] == team) \
                                    & (fp_stats_prev_week['NFL_WEEK'] == nfl_week)][fp_stat].values[0]
            # Set the 'ACTUAL_STAT_LINE' column in bovada_props_comparison using fp_stat_value
            bovada_props_comparison.loc[(bovada_props_comparison['PLAYER'] == player) & \
                                    (bovada_props_comparison['TEAM'] == team) & \
                                    (bovada_props_comparison['PROP'] == prop), 'ACTUAL_STAT_LINE'] = fp_stat_value
        except IndexError:
            continue
    else:
        try:
            # Get the value for the prop for the player during the given nfl week
            fp_stat_value1 = fp_stats_prev_week[(fp_stats_prev_week['PLAYER'] == player) \
                                    & (fp_stats_prev_week['TEAM'] == team) \
                                    & (fp_stats_prev_week['NFL_WEEK'] == nfl_week)][fp_stat[0]].values[0]
            # Get the value for the prop for the player during the given nfl week
            fp_stat_value2 = fp_stats_prev_week[(fp_stats_prev_week['PLAYER'] == player) \
                                    & (fp_stats_prev_week['TEAM'] == team) \
                                    & (fp_stats_prev_week['NFL_WEEK'] == nfl_week)][fp_stat[1]].values[0]
            # Combine these values for the total
            fp_stat_value = fp_stat_value1 + fp_stat_value2
            # Set the 'ACTUAL_STAT_LINE' column in bovada_props_comparison using fp_stat_value
            bovada_props_comparison.loc[(bovada_props_comparison['PLAYER'] == player) & \
                                    (bovada_props_comparison['TEAM'] == team) & \
                                    (bovada_props_comparison['PROP'] == prop), 'ACTUAL_STAT_LINE'] = fp_stat_value
        except:
            continue

# Convert ACTUAL_STAT_LINE to float for analysis
bovada_props_comparison['ACTUAL_STAT_LINE'] = pd.to_numeric(bovada_props_comparison['ACTUAL_STAT_LINE'], errors = 'coerce') 

# Compare the fp statistic to the BOVADA_LINE to find if projection correct side of line
bovada_props_comparison['CORRECT'] = bovada_props_comparison.apply(assessBovadaProp, axis = 1)
bovada_props_comparison['IMPLIED_OVER_PROBABILITY'] = bovada_props_comparison.apply(impliedOddsConverter, axis = 1)
bovada_props_comparison['CORRECT'] = bovada_props_comparison.apply(impliedOddsConverter, axis = 1)

# Update the bovada_props_comparison in postgres
for index, row in bovada_props_comparison.iterrows():
    upsertBovadaPropComparisons(row)

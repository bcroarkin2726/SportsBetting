# -*- coding: utf-8 -*-
"""
Created on Wed Oct  2 11:27:37 2019

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

# Connect to Twilio
client = Client(config.account_sid, config.auth_token)

# Set working directory to the file path of this file
abspath = os.path.abspath('PlayerPropAnalysis.py')
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
    this varies across values. Higher bovada_lines will give more weight to
    difference, while lower bovada_lines will give more weight to 
    pct_difference. The score will then be used to assign a grade.
    The maximum score is 100. 
    """
    difference = row['DIFFERENCE']
    pct_difference = row['PCT_DIFFERENCE']
    bovada_line = row['BOVADA_LINE']

    if bovada_line < 1:
        # in this extremely low category, nearly all weight should be given to pct difference
        diff_weight = .01
        pct_weight = .99
        diff_score = (difference / 20) * 50
        pct_score = pct_difference
        score = (diff_score * diff_weight) + (pct_score * diff_weight)
        return(score)
    elif bovada_line < 5:
        # in this extremely low category, nearly all weight should be given to pct difference
        diff_weight = .5
        pct_weight = .95
        diff_score = (difference / 20) * 50
        pct_score = pct_difference
        score = (diff_score * diff_weight) + (pct_score * diff_weight)
        return(score)
    elif bovada_line < 25:
        # in this very low category, most weight should be given to pct difference
        diff_weight = .2
        pct_weight = .8
        diff_score = (difference / 20) * 50
        pct_score = pct_difference
        score = (diff_score * diff_weight) + (pct_score * diff_weight)
        return(score)
    elif bovada_line < 50:
        # in this low category, more weight should be given to pct difference
        diff_weight = .35
        pct_weight = .65
        diff_score = (difference / 20) * 50
        pct_score = pct_difference
        score = (diff_score * diff_weight) + (pct_score * diff_weight)
        return(score)
    elif bovada_line < 100:
        # in this medium category, the categories should have even weights
        diff_weight = .5
        pct_weight = .5
        diff_score = (difference / 20) * 50
        pct_score = pct_difference
        score = (diff_score * diff_weight) + (pct_score * diff_weight)
        return(score)
    elif bovada_line < 200:
        # in this high category, more weight should be given to difference
        diff_weight = .65
        pct_weight = .35
        diff_score = (difference / 20) * 50
        pct_score = pct_difference
        score = (diff_score * diff_weight) + (pct_score * diff_weight)
        return(score)
    else:
        # in this very high category, most weight should be given to difference
        diff_weight = .8
        pct_weight = .2
        diff_score = (difference / 20) * 50
        pct_score = pct_difference
        score = (diff_score * diff_weight) + (pct_score * pct_weight)
        return(score)

def bet_grades(row):
    score = row['BET_SCORE']
    if score > 30.0: 
        return('A+')
    elif score > 20.0:
        return('A')
    elif score > 15.0:
        return('B+')
    elif score > 10.0:
        return('B')
    elif score > 7.0:
        return('C+')
    elif score > 5.0:
        return('C')
    elif score > 3.0:
        return('D+')
    elif score > 1.0:
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

def data_download_logging(table_name, current_date, current_time, requests_remaining = 0):
    """
    @table_name what data table has been updated
    @current_date the current date in a text string (ex: '11/20/2019')
    @current_time the current time in a text string (ex: '11:13:42')
    This function is meant for logging data pulls so they can be tracked 
    historically. This will help give daily logs of what was pulled and how
    often. 
    """
    try:
        connection = psycopg2.connect(user = "postgres",
                                      password = "RfC93TiD!ab",
                                      host = "127.0.0.1",
                                      port = "5432",
                                      database = "SportsBetting")
        cursor = connection.cursor()
        # Insert single record
        sql_insert_query = f"INSERT INTO data_download_logs (data_table_name, curr_date, curr_time, requests_remaining) \
        VALUES ($${table_name}$$, $${current_date}$$, $${current_time}$$, {requests_remaining})"
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
#league_id = 28265348
#year = 2019
#url = "https://fantasy.espn.com/apis/v3/games/ffl/leagueHistory/" + \
#      str(league_id) + "?seasonId=" + str(year)
#
#r = requests.get(url)
#d = r.json()[0]

##########################################################################
                
# I want to ensure that this script only runs at the proper times
# This would be Sunday, Monday, and Thursday starting at 10AM and stopping at 8PM
d = datetime.today()
day = d.weekday() # Monday is 0 and Sunday is 6
possible_days = [0, 3, 6]
hour = d.hour
possible_hours = [8,9,10,11,12,13,14,15,16,17,18,19,20]
if (day in possible_days) & (hour in possible_hours):
    
    ##################### BOVADA PLAYER PROPS ################################
    
    # Create an empty dataframe to append data to (excluding Def and K)
    bovada_props_comparison = pd.DataFrame(columns = ['NFL_WEEK', 'PLAYER', 'TEAM', \
                                'PROP', 'BOVADA_LINE', 'OVER_ODDS', 'IMPLIED_OVER_PROBABILITY', \
                                'UNDER_ODDS', 'IMPLIED_UNDER_PROBABILITY', 'FP_PROJECTION'])
    
    # We are getting the stats from the current week
    todays_date = datetime.now().strftime("%m/%d/%Y")
    nfl_week = findNFLWeek(todays_date)
    
    # USING THE ACTUAL API
    bovada_url = 'https://www.bovada.lv/services/sports/event/v2/events/A/description/football/nfl'
    bovada_response = requests.get(bovada_url)
    bovada_txt = bovada_response.text
    
    ## USING THE TXT FILE (TESTING)
    #with open('BovadaAPI.txt', 'r') as file:
    #    bovada_txt = file.read()
    
    # Format the json
    bovada_json = json.loads(bovada_txt)
    bovada_events = bovada_json[0]['events']
    
    # Iterate over bovada_events to extract the different player props
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
                    if len(player_prop['outcomes']) > 0: # only if there are any player props available
                        line = player_prop['outcomes'][0]['price']['handicap']
                        over_odds = player_prop['outcomes'][0]['price']['american'] # odds for the over
                        implied_over_probability = impliedOddsConverter(over_odds)
                        under_odds = player_prop['outcomes'][1]['price']['american'] # odds for the under
                        implied_under_probability = impliedOddsConverter(under_odds)
                        team = find_between(player_prop['id'],'(', ')')
                        prop_list = [nfl_week, player, team, prop, line, over_odds, \
                                     implied_over_probability, under_odds, implied_under_probability, '']
                        # Append the list to the dataframe         
                        bovada_props_comparison.loc[len(bovada_props_comparison)] = prop_list
                    else:
                        continue
    
    ######################### FANTASY PROS PROJECTIONS ############################
    
    ### Create fantasy statistics in one table for QB, RB, WR, TE, DST, and K
    
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
                        'Buffalo Bills': 'BUF',
                        'Chicago Bears': 'CHI',
                        'Indianapolis Colts': 'IND',
                        'Oakland Raiders': 'OAK',
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
    for position, url in fantasy_pros_projection_urls.items():  
        # Get the stat keys lookup for position
        lookup = stats_lookup[position]
        # Lookup the fpts index 
        fpts_index = position_fpts_index[position]
        # Web scrape Fantasy Pros for relevant information
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        projections = list(list(list(list(list(list(list(soup.children)[25].children)[1])[1])[1])[11])[1])[3]
        projections_list =  list(projections)
        nfl_week = int(find_between(str(list(list(list(soup.children)[2])[1])[1]), 'Week ', ' ' + position))
        for num, item in enumerate(projections_list):
            if item != '\n':
                # Create an empty list to update the data for
                player_projections = [0] * 27
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
                team = list(proj_list[0])[1].strip() if position != 'DST' else team_abrv_lookup[find_between(str(list(proj_list[0])[0]), '>', '<')]
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
    
    ############### APPEND FP PROJECTIONS TO BOVADA PLAYER PROPS ##################
        
    ### Now that we have FP projections, we can compare them to the Bovada player
    ### props to see where there is value
    
    # Create a lookup between the Bovada prop and the equivalent FP stat    
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
                   'Longest Completion': 'N/A',
                   'Total Yards on 1st Rushing Attempt': 'N/A',
                   'Total Rushing Attempts in the game': 'N/A'}
    
    # Create a lookup between NFL player names from Bovada and FP where there are discrepancies
    # Name on the left is from Bovada and name on the right is FP
    player_lookup = {'Patrick Mahomes II': 'Patrick Mahomes',
                     'Dermarcus Robinson': 'Demarcus Robinson',
                     'Desean Hamilton': 'DaeSean Hamilton'}
    
    # Iterate over bovada_props_comparison and add in fp projections where applicable
    for index, row in bovada_props_comparison.iterrows():
        # Need to convert player names to find them in FP
        player = row['PLAYER']
        player = player_lookup[player] if player in player_lookup.keys() else player
        prop = row['PROP']
        prop_lookup = prop_lookups[prop]
        fp_projection = fp_projections[fp_projections['PLAYER'] == player][prop_lookup].values[0] \
            if (prop_lookup != 'N/A') & (len(fp_projections[fp_projections['PLAYER'] == player]) > 0) else 0
        fp_projection = fp_projection if type(fp_projection) in [int, float, np.float64] else round(fp_projection[0] + fp_projection[1],1)
        # append the fp_projection to the bovada table
        bovada_props_comparison.loc[index, 'FP_PROJECTION'] = fp_projection
    
    # Remove Props from bovada_props_comparison that I don't use (Longest Completion and Longest Reception)
    unused_props = ['Longest Completion', 'Longest Reception', 'Total Interceptions Thrown']
    bovada_props_comparison = bovada_props_comparison[(bovada_props_comparison['PROP'] != unused_props[0]) & 
        (bovada_props_comparison['PROP'] != unused_props[1]) 
        & (bovada_props_comparison['PROP'] != unused_props[2])]    
        
    # Find difference bt Bovada line and FP projection
    bovada_props_comparison['BOVADA_LINE'] = pd.to_numeric(bovada_props_comparison['BOVADA_LINE'], errors = 'coerce') # convert to float for analysis
    bovada_props_comparison['FP_PROJECTION'] = pd.to_numeric(bovada_props_comparison['FP_PROJECTION'], errors = 'coerce') # convert to float for analysis
    bovada_props_comparison['DIFFERENCE'] = bovada_props_comparison['BOVADA_LINE'] - bovada_props_comparison['FP_PROJECTION']
    bovada_props_comparison['DIFFERENCE'] = abs(bovada_props_comparison['DIFFERENCE'])
    bovada_props_comparison['PCT_DIFFERENCE'] = abs(round((bovada_props_comparison['BOVADA_LINE']/bovada_props_comparison['FP_PROJECTION'] - 1) * 100, 2))
    
    # Drop any rows with a PCT_DIFFERENCE of inf as this is likely an error
    bovada_props_comparison = bovada_props_comparison.replace([np.inf, -np.inf], np.nan).dropna(subset=["PCT_DIFFERENCE"], how="all")
    
    # Create bet grades for each row based on difference bt Bovada line and FP projection
    bovada_props_comparison['DIRECTION'] = bovada_props_comparison.apply(over_under, axis = 1)
    bovada_props_comparison['BET_SCORE'] = bovada_props_comparison.apply(bet_scores, axis = 1)
    bovada_props_comparison['BET_GRADE'] = bovada_props_comparison.apply(bet_grades, axis = 1)
    
    # Add empty place holder columns for comparing actual performance to the bet grades
    bovada_props_comparison['ACTUAL_STAT_LINE'] = -1 # Default missing stat line value
    bovada_props_comparison['CORRECT'] = ''
    
    # Upload the bovada_props_comparison to a postgres table
    for index, row in bovada_props_comparison.iterrows():
        upsertBovadaPropComparisons(row)
    
    # Log the Bovada Player Prop download
    d = datetime.today()
    CurrentDate = d.strftime('%m/%d/%Y')
    CurrentTime = d.strftime('%H:%M:%S')
    data_download_logging('bovada_props_comparison', CurrentDate, CurrentTime)

else:
    # If we are not in the possible days or hours for this script, then there
    # is no point in running, so we can just continue. This is done to ensure 
    # that there are no unnecessary runs of the script with the Windows Task
    # Scheduler
    pass

################################## NOTES ######################################
        
# 1. There appears to be a minor glitch with Fantasy Pros where it does not list 
#    fantasy point for certain low scoring players. For example, Tavon Austin is 
#    listed in Week 6 as having 5 receptions for 64 yards, yet has 0 FPTS. Could 
#    get around this by calculating FPTS from my end.
# 2. Fantasy Pros does not list PA or yds_agn for DST. They also appear to have 
#    a different scoring system for DST since I have seen numerous discrepancies 
#    between the FPTS listed on FP and that on ESPN.





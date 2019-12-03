# -*- coding: utf-8 -*-
"""
Created on Mon Sep  9 12:53:52 2019

@author: Brandon Croarkin
"""

import requests
from datetime import datetime
import pandas as pd
import json
from calendar import monthrange
import psycopg2
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath('config.py')) + '\\Documents\\GitHub\\SportsBetting')
import config

############################ Twilio Connection ################################

# Download the helper library from https://www.twilio.com/docs/python/install
from twilio.rest import Client

# Connect to Twilio
client = Client(config.account_sid, config.auth_token)

########################### Custom Functions ##################################

def myround(number):
    """Round a number to the closest half integer.
    >>> round_of_rating(1.3)
    1.5
    >>> round_of_rating(2.6)
    2.5
    >>> round_of_rating(3.0)
    3.0
    >>> round_of_rating(4.1)
    4.0"""

    return round(number * 2) / 2

def findNFLWeek(Date):
   try:
        connection = psycopg2.connect(user = config.psycopg2_username,
                                      password = config.psycopg2_password,
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

def findGameID(HomeTeam, CommenceTimeShort):
   try:
        connection = psycopg2.connect(user = config.psycopg2_username,
                                      password = config.psycopg2_password,
                                      host = "127.0.0.1",
                                      port = "5432",
                                      database = "SportsBetting")
        cursor = connection.cursor()
        # Check if row already exists
        sql_select_query = f"SELECT gameid FROM nflgames WHERE hometeam = $${HomeTeam}$$ \
        AND commencetimeshort = $${CommenceTimeShort}$$"
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

def upsertNFLGames(CommenceTimeLong, CommencetimeShort, NFL_Week, HomeTeam, AwayTeam):
   try:
        connection = psycopg2.connect(user = config.psycopg2_username,
                                      password = config.psycopg2_password,
                                      host = "127.0.0.1",
                                      port = "5432",
                                      database = "SportsBetting")
        cursor = connection.cursor()
        # Check if row already exists
        sql_select_query = f"SELECT * FROM nflgames WHERE commencetimeshort = $${CommenceTimeShort}$$ AND hometeam = $${HomeTeam}$$"
        cursor.execute(sql_select_query)
        results = cursor.fetchone()
        if results:
            # If there are results that means the row is already there and should just be updated
            sql_update_query = f"UPDATE nflgames SET commencetimelong = $${CommenceTimeLong}$$, commencetimeshort = \
            $${CommenceTimeShort}$$, nfl_week = {NFL_Week}, hometeam = $${HomeTeam}$$, awayteam = $${AwayTeam}$$ \
            WHERE commencetimeshort = $${CommenceTimeShort}$$ AND hometeam = $${HomeTeam}$$"
            cursor.execute(sql_update_query)
            connection.commit()
        else:
            # Insert single record
            sql_insert_query = f"INSERT INTO nflgames (commencetimelong, commencetimeshort, nfl_week, hometeam, awayteam) \
            VALUES ($${CommenceTimeLong}$$, $${CommenceTimeShort}$$, {NFL_Week}, $${HomeTeam}$$, $${AwayTeam}$$)"
            cursor.execute(sql_insert_query)
            connection.commit()
   except (Exception, psycopg2.Error) as error:
       print("Error in operation", error)
   finally:
       # closing database connection.
       if (connection):
           cursor.close()
           connection.close()

def insertNFLOdds(GameID, CurrentDate, CurrentTime, Website, BetType, HomeOdds, AwayOdds, HomePoints, AwayPoints):
   try:
        connection = psycopg2.connect(user = config.psycopg2_username,
                                      password = config.psycopg2_password,
                                      host = "127.0.0.1",
                                      port = "5432",
                                      database = "SportsBetting")
        cursor = connection.cursor()
        # Insert single record
        sql_insert_query = f"INSERT INTO nflodds (gameid, currentdate, currenttime, website, bet_type, home_odds, away_odds, home_points, away_points) \
        VALUES ({GameID}, $${CurrentDate}$$, $${CurrentTime}$$, $${Website}$$, $${BetType}$$, {HomeOdds}, {AwayOdds}, {HomePoints}, {AwayPoints})"
        cursor.execute(sql_insert_query)
        connection.commit()
   except (Exception, psycopg2.Error) as error:
       print("Error in operation", error)
   finally:
       # closing database connection.
       if (connection):
           cursor.close()
           connection.close()

def requestsOnPace(requests_remaining):
    # Get the current day and time
    now = datetime.now()
    day = now.day
    hour = now.hour
    year = now.year
    month = now.month
    
    # Find out how many days in the current month
    days_in_month = monthrange(year, month)[1]
    hours_in_month = days_in_month * 24
    
    # find the percent through the month
    hours_into_month = day * 24 + hour
    percent_through_month = hours_into_month / hours_in_month
    
    # Find out the percentage of requests used (500 a month)
    requests_used_percent = (500 - requests_remaining) / 500
    
    # Return True or False depending on whether I am ahead/behind requests
    if percent_through_month > requests_used_percent:
        return(True)
    else:
        return(False)

def performAPIPull():
    """
    The automatic nature of the script running seems to be unpredictable, with it running
    multiple time within the hour plus within the 4 hour gaps. Since we are working with a
    limited number of monthly requests we need to be able to prevent. This function will 
    serve this purpose by checking some requirments before making an API pull. 
    Requirements:
            1. There is a time gap between requests (this will vary based on day of week)
                a. 1 hour gap on Monday (most fluctuations occur here)
                b. 2 hour gap on Tuesday 
                c. 3 hour gap all other days
            2. Only run during certain hours (between 6am and 8pm)
    """
    try:
        connection = psycopg2.connect(user = config.psycopg2_username,
                                      password = config.psycopg2_password,
                                      host = "127.0.0.1",
                                      port = "5432",
                                      database = "SportsBetting")
        cursor = connection.cursor()
        # Check if row already exists
        sql_select_query = f"SELECT currentdate, currenttime FROM nflodds"
        cursor.execute(sql_select_query)
        results = cursor.fetchall()
    except (Exception, psycopg2.Error) as error:
        print("Error in operation", error)
    finally:
       # closing database connection.
       if (connection):
           cursor.close()
           connection.close()
           
    # Format the data pulled to find the most recent date and time
    results_df = pd.DataFrame(results, columns = ['CurrentDate', 'CurrentTime'])
    results_df.sort_values(by = ['CurrentDate', 'CurrentTime'], ascending = False, inplace = True)
    results_df.reset_index(inplace = True)
    results_df = results_df[['CurrentDate', 'CurrentTime']]
    last_pull_date, last_pull_time = results_df.loc[0]
    
    # Format the last_pull_date and last_pull_time
    last_pull = last_pull_date + ' ' + last_pull_time
    last_pull = datetime.strptime(last_pull, "%m/%d/%Y %H:%M:%S")
    
    # Get the current day and time for comparison
    now = datetime.now()

    # Find the difference between the two times in hours
    delta = now - last_pull
    delta_hours = round(delta.days * 24 + delta.seconds / 3600.0, 1)
    
    # Use the current day to set the hour_gap (we want more pulls earlier in the week)
    day = now.weekday() # Monday is 0 and Sunday is 6
    hour_gap_lookup = {0: 1,
                       1: 2,
                       2: 3,
                       3: 3,
                       4: 3,
                       5: 3,
                       6: 3}
    hour_gap = hour_gap_lookup[day]
    
    # We don't want to pull between the hours of 9pm to 5am
    hour = now.hour

    # Return True or False based on whether we are inside or outside hour gap
    if (delta_hours >= hour_gap) & (5 < hour < 21):
        return(True)
    else:
        return(False)
        
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
        connection = psycopg2.connect(user = config.psycopg2_username,
                                      password = config.psycopg2_password,
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

def findHour(currenttime):
    """
    @currenttime the time of an API pull (ex: '14:54:12')
    This function takes the current time and output the hour.
    Example: '14:54:12' --> 14
    """
    return(currenttime.split(':')[0])

def fetchNFLOdds(NFL_Week):
    """
    @NFL_Week the NFL gameweek we are pulling the odds for.
    This function pulls all the NFL odds for a given NFL week. 
    Since the NFL week is not already in the nfl odds table, we first need to 
    get all the gameid's for a given NFL week. 
    """
    try:
        connection = psycopg2.connect(user = config.psycopg2_username,
                                      password = config.psycopg2_password,
                                      host = "127.0.0.1",
                                      port = "5432",
                                      database = "SportsBetting")
        cursor = connection.cursor()
        # Pull all game ids for the NFL week
        sql_select_query = f"SELECT * FROM nflodds WHERE gameid IN (SELECT gameid FROM nflgames WHERE nfl_week = {NFL_Week}) ORDER BY gameid;"
        cursor.execute(sql_select_query)
        nflodds = cursor.fetchall()
        if nflodds:
            return(pd.DataFrame(nflodds, columns = ['nfloddsid', 'gameid', 'currentdate', 
                                                            'currenttime', 'website', 'bet_type',
                                                            'home_odds', 'away_odds', 'home_points',
                                                            'away_points']))
        else:
            return('No NFL Odds for the week yet.')
    except (Exception, psycopg2.Error) as error:
       print("Error in operation", error)
    finally:
       # closing database connection.
       if (connection):
           cursor.close()
           connection.close()
           
def fetchGameInfo(game_id):
    """
    @game_id the unique id assigned to an NFL game
    This function uses the game_id given to return information on the game 
    including: home team, away team, and the commence time
    """
    try:
        connection = psycopg2.connect(user = config.psycopg2_username,
                                      password = config.psycopg2_password,
                                      host = "127.0.0.1",
                                      port = "5432",
                                      database = "SportsBetting")
        cursor = connection.cursor()
        # Pull all home team, away team, and commence time
        sql_select_query = f"SELECT hometeam, awayteam, commencetimelong FROM nflgames WHERE gameid = {game_id}"
        cursor.execute(sql_select_query)
        game_info = cursor.fetchall()
        if game_info:
            return(game_info[0])
        else:
            return('No data found for given game_id ({game_id}).')
    except (Exception, psycopg2.Error) as error:
       print("Error in operation", error)
    finally:
       # closing database connection.
       if (connection):
           cursor.close()
           connection.close()

def probabilityConverter(nfl_odds):
    """
    @nfl_odds the decimal odds for a given NFL game (ex. 1.909)
    This function takes in decimal odds and converts it to the implied
    probability of winning.
    Ex: 1.909 --> 52.4%
    """
    return(round((1/ nfl_odds) * 100,1))
    
def multipleDataPulls(nfl_odds_df):
    """
    @nfl_odds_df the nflodds dataframe downloaded from PostgreSQL
    This function checks to see if there is more than one data pull for a given
    NFL week. If it does, the function returns True and will look for line
    movements. If it doesn't, the function returns False and stops.
    """
    # Find the first GameID
    gameid = nflodds['gameid'].sort_values().values[0]
    # Check if there are multiple spread bets for Bovada for that gameid
    df = nflodds[(nflodds['gameid'] == gameid) & (nflodds['website'] == 'Bovada') & (nflodds['bet_type'] == 'Spread')].drop_duplicates(subset = ['gameid', 'currentdate', 'currenttime', 'website', 'bet_type'])
    return(len(df) > 1)
    
############################## API Pull #######################################

# To get odds for a sepcific sport, use the sport key from the last request
#   or set sport to "upcoming" to see live and upcoming across all sports
sport_key = 'americanfootball_nfl'

if performAPIPull(): #only pull if last request was outside of hour gap
    
    odds_response = requests.get('https://api.the-odds-api.com/v3/odds', params={
        'api_key': config.api_key,
        'sport': sport_key,
        'region': 'us', # uk | us | au
        'mkt': 'h2h' # h2h | spreads | totals
    })
        
    spreads_response = requests.get('https://api.the-odds-api.com/v3/odds', params={
        'api_key': config.api_key,
        'sport': sport_key,
        'region': 'us', # uk | us | au
        'mkt': 'spreads' # h2h | spreads | totals
    })
        
    totals_response = requests.get('https://api.the-odds-api.com/v3/odds', params={
        'api_key': config.api_key,
        'sport': sport_key,
        'region': 'us', # uk | us | au
        'mkt': 'totals' # h2h | spreads | totals
    })
    
    odds_json = json.loads(odds_response.text)['data']
    
    spreads_json = json.loads(spreads_response.text)['data']
    
    totals_json = json.loads(totals_response.text)['data']
    
    ############################## Format JSON ####################################
    
    # Create a dictionary for json and their bet type
    bet_type_dict = {0: 'Moneyline',
                     1: 'Spread',
                     2: 'O/U'}
    
    # Iterate over JSONs, extract needed data, and add to PostgreSQL tables
    for num, json_dict in enumerate([odds_json, spreads_json, totals_json]):
        for x in json_dict:
            CommenceTimeShort = datetime.fromtimestamp(x['commence_time']).strftime("%m/%d/%Y")
            CommenceTimeLong = datetime.fromtimestamp(x['commence_time']).strftime("%A, %B %d, %Y %I:%M:%S")
            HomeTeam = x['teams'][1]
            AwayTeam = x['teams'][0]
            NFL_Week = findNFLWeek(CommenceTimeShort)
            upsertNFLGames(CommenceTimeLong, CommenceTimeShort, NFL_Week, HomeTeam, AwayTeam)
            for y in x['sites']:
                GameID = findGameID(HomeTeam, CommenceTimeShort)
                CurrentDate = datetime.fromtimestamp(y['last_update']).strftime("%m/%d/%Y")
                CurrentTime = datetime.fromtimestamp(y['last_update']).strftime("%H:%M:%S")
                Website = y['site_nice']
                BetType = bet_type_dict[num]
                if BetType == 'Moneyline':
                    HomePoints = 0
                    AwayPoints = 0
                    HomeOdds = y['odds']['h2h'][0]
                    AwayOdds = y['odds']['h2h'][1]
                    insertNFLOdds(GameID, CurrentDate, CurrentTime, Website, BetType, HomeOdds, AwayOdds, HomePoints, AwayPoints)
                elif BetType == 'Spread':
                    HomePoints = y['odds']['spreads']['points'][0]
                    AwayPoints = y['odds']['spreads']['points'][1]
                    HomeOdds = y['odds']['spreads']['odds'][0]
                    AwayOdds = y['odds']['spreads']['odds'][1]
                    insertNFLOdds(GameID, CurrentDate, CurrentTime, Website, BetType, HomeOdds, AwayOdds, HomePoints, AwayPoints)
                else:
                    HomePoints = y['odds']['totals']['points'][0]
                    AwayPoints = y['odds']['totals']['points'][1]
                    HomeOdds = y['odds']['totals']['odds'][0]
                    AwayOdds = y['odds']['totals']['odds'][1]
                    insertNFLOdds(GameID, CurrentDate, CurrentTime, Website, BetType, HomeOdds, AwayOdds, HomePoints, AwayPoints)
    
    # Check how many requests I have left in the month
    requests_remaining = odds_response.headers['x-requests-remaining']
    
    # Send download log to data_download_logs
    data_download_logging("nflodds", CurrentDate, CurrentTime, requests_remaining)
        
############################## Line Tracking ##################################

# Pull in the NFL odds for the current week
nflodds = fetchNFLOdds(NFL_Week)

# Only can track line changes after more than one value, need to check this first
if multipleDataPulls(nflodds):
    
    # Find all the game ids for the week and add to a list
    nflgames = nflodds.gameid.unique() 
    
    # Create a variable to hold all the line movements so we only need to send one message
    text_message = ''
    
    # Loop over the game ids and see how much they have changed
    for game in nflgames:
        # subset the dataset to just the single game
        nflodds_sub = nflodds[nflodds['gameid'] == game]
        # find what teams are involved in this game and when the game is
        home_team, away_team, commencetimelong = fetchGameInfo(game)
        # Only care about the spread and O/U since spread and ML move in parallel
        for bet_type in ['O/U', 'Spread']:
            nflodds_sub2 = nflodds_sub[nflodds_sub['bet_type'] == bet_type]
            # Sort by currentdate and current time
            nflodds_sub2.sort_values(by = ['currentdate', 'currenttime'], ascending = False, inplace = True)
            # Create a column with the hour of the pull
            nflodds_sub2['currenthour'] = nflodds_sub2.loc[:,'currenttime'].apply(findHour)
            # Break out logic based on whether this is O/U or Spread
            if bet_type == 'O/U':
                # Filter the df to just the columns I need
                nflodds_sub3 = nflodds_sub2[['currentdate', 'currenthour', 'home_points']]
                # Ensure the home_points column is numeric
                nflodds_sub3['home_points'] = pd.to_numeric(nflodds_sub3['home_points'])
                # Group the data by website and hour of currenttime
                nflodds_grouped = nflodds_sub3.groupby(['currentdate', 'currenthour']).mean()
                # Reset the index and sort nflodds_grouped
                nflodds_grouped.reset_index(inplace = True)
                nflodds_grouped.sort_values(by = ['currentdate', 'currenthour'], 
                                            ascending = False, inplace = True)
                nflodds_grouped.reset_index(drop = True, inplace = True)
                # Round all points to nearest .5 or whole number
                nflodds_grouped['home_points'] = nflodds_grouped['home_points'].apply(myround)
                # Compare the two most recent lines and the opening line
                opening_line = nflodds_grouped['home_points'][len(nflodds_grouped)-1]
                current_line = nflodds_grouped['home_points'][0]
                previous_line = nflodds_grouped['home_points'][1]
                line_difference = current_line - previous_line
                # If the consenus line has moved by .5, we should add this to the message
                if abs(current_line - previous_line) > 0:
                    text_message += f"The O/U for {home_team} vs. {away_team} on {commencetimelong} has moved by {line_difference}. Current line is {current_line}. Previous line was {previous_line}. Opening line was {opening_line}.\n"
            else: # Spread
                # Filter the df to just the columns I need
                nflodds_sub3 = nflodds_sub2[['currentdate', 'currenthour', 'home_odds', 'away_odds', 'home_points']]
                # Ensure the home_odds, away_odds, and home_points columns are numeric
                nflodds_sub3['home_odds'] = pd.to_numeric(nflodds_sub3['home_odds'])
                nflodds_sub3['away_odds'] = pd.to_numeric(nflodds_sub3['away_odds'])
                nflodds_sub3['home_points'] = pd.to_numeric(nflodds_sub3['home_points'])    
                # Convert all the odds columns to probabilities and then drop odds
                nflodds_sub3['home_prob'] = nflodds_sub3['home_odds'].apply(probabilityConverter)
                del nflodds_sub3['home_odds']
                nflodds_sub3['away_prob'] = nflodds_sub3['away_odds'].apply(probabilityConverter)
                del nflodds_sub3['away_odds']
                # Group the data by website and hour of currenttime
                nflodds_grouped = nflodds_sub3.groupby(['currentdate', 'currenthour']).mean()
                # Reset the index and sort nflodds_grouped
                nflodds_grouped.reset_index(inplace = True)
                nflodds_grouped.sort_values(by = ['currentdate', 'currenthour'], 
                                            ascending = False, inplace = True)
                nflodds_grouped.reset_index(drop = True, inplace = True)
                # Round all points and probabilities to nearest .5 or whole number
                nflodds_grouped['home_prob'] = nflodds_grouped['home_prob'].apply(myround)
                nflodds_grouped['away_prob'] = nflodds_grouped['away_prob'].apply(myround)
                nflodds_grouped['home_points'] = nflodds_grouped['home_points'].apply(myround)            
                # Compare the two most recent lines and the opening line
                opening_line = nflodds_grouped['home_points'][len(nflodds_grouped)-1]
                current_line = nflodds_grouped['home_points'][0]
                previous_line = nflodds_grouped['home_points'][1]
                line_difference = current_line - previous_line
                opening_home_prob = nflodds_grouped['home_prob'][len(nflodds_grouped)-1]
                previous_home_prob = nflodds_grouped['home_prob'][1]
                current_home_prob = nflodds_grouped['home_prob'][0]
                opening_away_prob = nflodds_grouped['away_prob'][len(nflodds_grouped)-1]
                previous_away_prob = nflodds_grouped['away_prob'][1]
                current_away_prob = nflodds_grouped['away_prob'][0]
                # If the consenus line has moved by .5, we should add this to the message
                if (abs(current_line - previous_line) > 0) or (abs(current_home_prob - previous_home_prob) > 0) or (abs(current_away_prob - previous_away_prob) > 0):
                    # Add the movement to the message if the line moves by .5 points or the home/away odds move by .5 probability
                    text_message += f"The Spread for {home_team} vs. {away_team} on {commencetimelong} has moved by {line_difference}.\
                    Current line is {current_line} with home/away probabilities of {current_home_prob}/{current_away_prob}. \
                    Previous line was {previous_line} with home/away probabilities of {previous_home_prob}/{previous_away_prob}. \
                    Opening line was {opening_line} with home/away probabilities of {opening_home_prob}/{opening_away_prob}.\n"
    
    # List of phone numbers to send the updates to
    phone_contact_list = ['+15712718265', '+15719195300']
    
    for number in phone_contact_list:
        text_message = client.messages.create(
                             body = text_message,
                             from_ = '+12562911093',
                             to = number)

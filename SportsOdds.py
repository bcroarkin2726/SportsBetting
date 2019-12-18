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

pd.set_option('mode.chained_assignment', None)

############################ Twilio Connection ################################

# Download the helper library from https://www.twilio.com/docs/python/install
from twilio.rest import Client

# Connect to Twilio
client = Client(config.account_sid, config.auth_token)

############################ Email Connection ################################

import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

port = 465  # For SSL
password = config.gmail_password

# Create a secure SSL context
context = ssl.create_default_context()

# Email here
sender_email = "bofabet677@gmail.com"

########################### Custom Functions ##################################

def myround(number, decimal = 0.5, precision = 2):
    """
    @number the number given to the function to round
    @decimal the decimal figure you want to round to the nearest
    @precision the number of places after the decimal to return
    Round a number to the closest half integer.
    >>> round_of_rating(1.3, .5)
    1.5
    >>> round_of_rating(3.0, .25)
    3.0
    >>> round_of_rating(4.15, .25)
    4.25
    """
    # Set the acceptable decimals to allow
    acceptable_decimals = [.25, .50]
    
    if decimal in acceptable_decimals:
        # Round the decimal given to 2 signicant figures
        decimal_round = round(decimal, precision)
        # Create a lookup dictionary to alter the precion level
        decimal_lookup = {.50: 2,
                          .25: 4}
        
        return round(number * decimal_lookup[decimal_round]) / decimal_lookup[decimal_round]
    else:
        return(number)

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

def decimal2ProbabilityConverter(nfl_odds):
    """
    @nfl_odds the decimal odds for a given NFL game (ex. 1.909)
    This function takes in decimal odds and converts it to the implied
    probability of winning.
    Ex: 1.909 --> 52.4%
    """
    return(round((1/ nfl_odds) * 100,1))
    
def decimal2AmericanConverter(nfl_odds):
    """
    @nfl_odds the decimal odds for a given NFL game (ex. 1.909)
    This function takes in decimal odds and converts it to the American
    line.
    Ex: 1.9091 --> -110
    """
    if nfl_odds < 2:
        return(str(round((-100)/(nfl_odds - 1))))
        
    else:
        return('+' + str(round((nfl_odds - 1) * 100)))

def probability2AmericanConverter(win_probability):
    """
    @win_probability the percent odds for a team to win a game in decimal
    format (ex. .652 )
    This function takes in win probability and converts it to the American odds
    Ex: .65 --> -185.7
    """
    # Need to convert the win probabilty to a 0-1 scale if not already
    if (win_probability >= 1) & (win_probability < 100):
        win_probability = win_probability / 100
    elif (win_probability > 0) & (win_probability < 1):
        pass
    else:
        print("bad win probability")
        
    # Convert the win probability to the American odd    
    if win_probability < .5:
        return('+' + str(round((100 - (100 * win_probability)) / win_probability)))
    else:
        return(str(round((-100 * win_probability)/(1 - win_probability))))
        
def multipleDataPulls(nfl_odds_df, nfl_week):
    """
    @nfl_odds_df the nflodds dataframe downloaded from PostgreSQL
    @ nfl_week the current NFL week
    This function checks to see if there is more than one data pull for a given
    NFL week. If it does, the function returns True and will look for line
    movements. If it doesn't, the function returns False and stops.
    """
    # Find the most recent game from Bovada pulled into nflodds
    try:
        connection = psycopg2.connect(user = config.psycopg2_username,
                                      password = config.psycopg2_password,
                                      host = "127.0.0.1",
                                      port = "5432",
                                      database = "SportsBetting")
        cursor = connection.cursor()
        # Pull the most recent gameid pulled from Bovada
        sql_select_query = f"SELECT * FROM nflodds \
        WHERE gameid = (select max(gameid) from nflgames WHERE nfl_week = $${nfl_week}$$) AND bet_type = 'Spread' AND website = 'Bovada' \
        ORDER BY currentdate DESC, currenttime DESC;"
        cursor.execute(sql_select_query)
        results = cursor.fetchall()
        return(len(results) > 1)
    except (Exception, psycopg2.Error) as error:
       print("Error in operation", error)
    finally:
       # closing database connection.
       if (connection):
           cursor.close()
           connection.close()

def newNFLWeek():
    """
    The goal of the function is to send a text update when Bovada posts lines
    for the upcoming NFL week. 
    Finds the most recent game pulled and pulls all spread records for that
    game from Bovada. If there is just 1 row, this means Bovada just posted
    those odds and we should send a text alert. 
    """
    # Find the most recent game from Bovada pulled into nflodds
    try:
        connection = psycopg2.connect(user = config.psycopg2_username,
                                      password = config.psycopg2_password,
                                      host = "127.0.0.1",
                                      port = "5432",
                                      database = "SportsBetting")
        cursor = connection.cursor()
        # Pull the most recent gameid pulled from Bovada
        sql_select_query = f"SELECT * FROM nflodds \
        WHERE gameid = (select max(gameid) from nflodds) AND bet_type = 'Spread' AND website = 'Bovada' \
        ORDER BY currentdate DESC, currenttime DESC;"
        cursor.execute(sql_select_query)
        results = cursor.fetchall()
        if len(results) == 1:
            # List of phone numbers to send the updates to
#            phone_contact_list = ['+15712718265', '+15719195300']
            phone_contact_list = ['+15712718265']
            for number in phone_contact_list:
                message = client.messages.create(
                                     body = f"Bovada lines have been posted for NFL Week {NFL_Week}.",
                                     from_ = '+12562911093',
                                     to = number)
    except (Exception, psycopg2.Error) as error:
       print("Error in operation", error)
    finally:
       # closing database connection.
       if (connection):
           cursor.close()
           connection.close()
    
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
    
    # Send a message about successful download of NFL odds
    message = client.messages.create(
                         body=f"NFL odds were downloaded on {CurrentDate} at {CurrentTime}. You have {requests_remaining} requests remaining.",
                         from_='+12562911093',
                         to='+15712718265')
    
    # Send a text message if this is for a new NFL Week
    newNFLWeek() 

    # Send download log to data_download_logs
    data_download_logging("nflodds", CurrentDate, CurrentTime, requests_remaining)
        
############################## Line Tracking ##################################

# Find the current NFL week
d = datetime.today()
CurrentDate = d.strftime('%m/%d/%Y')
NFL_Week = findNFLWeek(CurrentDate)
    
# Pull in the NFL odds for the current week
nflodds = fetchNFLOdds(NFL_Week)

# Only can track line changes after more than one value, need to check this first
if multipleDataPulls(nflodds, NFL_Week):
    
    # Find all the game ids for the week and add to a list
    nflgames = nflodds.gameid.unique() 
    
    # Set needed variables
    receiver_email = "loudoun5@yahoo.com"
    message = MIMEMultipart("alternative")
    message["Subject"] = "NFL Odds Movements - Test"
    message["From"] = "bofabet677@gmail.com"
    message["To"] = "loudoun5@yahoo.com"
        
    # Initialize the spread and o/u message
    spread_message = ""
    ou_message = ""
        
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
                nflodds_sub3 = nflodds_sub2[['currentdate', 'currenthour', 'home_odds', 'away_odds', 'home_points']]
                # Ensure the home_odds, away_odds, and home_points columns are numeric
                nflodds_sub3['home_points'] = pd.to_numeric(nflodds_sub3.loc[:,'home_points'])
                nflodds_sub3['home_odds'] = pd.to_numeric(nflodds_sub3.loc[:,'home_odds'])
                nflodds_sub3['away_odds'] = pd.to_numeric(nflodds_sub3.loc[:,'away_odds'])
                # Convert all the odds columns to probabilities and then drop odds
                nflodds_sub3['home_prob'] = nflodds_sub3['home_odds'].apply(decimal2ProbabilityConverter)
                del nflodds_sub3['home_odds']
                nflodds_sub3['away_prob'] = nflodds_sub3['away_odds'].apply(decimal2ProbabilityConverter)
                del nflodds_sub3['away_odds']
                # Group the data by website and hour of currenttime
                nflodds_grouped = nflodds_sub3.groupby(['currentdate', 'currenthour']).mean()
                # Reset the index and sort nflodds_grouped
                nflodds_grouped.reset_index(inplace = True)
                nflodds_grouped.sort_values(by = ['currentdate', 'currenthour'], 
                                            ascending = False, inplace = True)
                nflodds_grouped.reset_index(drop = True, inplace = True)
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
                # Convert all the prob columns to American odds
                opening_home_prob = probability2AmericanConverter(opening_home_prob)
                previous_home_prob = probability2AmericanConverter(previous_home_prob)
                current_home_prob = probability2AmericanConverter(current_home_prob)
                opening_away_prob = probability2AmericanConverter(opening_away_prob)
                previous_away_prob = probability2AmericanConverter(previous_away_prob)
                current_away_prob = probability2AmericanConverter(current_away_prob)
                # Round all points and probabilities to nearest .5 or whole number
                opening_line = myround(opening_line, decimal = .25)
                current_line = myround(current_line, decimal = .25)
                previous_line = myround(previous_line, decimal = .25)
                line_difference = myround(line_difference, decimal = .25)
                # If the consenus line has moved by .5, we should add this to the message
                if abs(current_line - previous_line) >= 0.25:
                    ou_message += f"<p>The O/U for <b>{home_team}</b> vs. <b>{away_team}</b> on {commencetimelong} has moved by {line_difference}.<br>\
                    Current line is {current_line} with home/away probabilities of {current_home_prob}/{current_away_prob}.<br>\
                    Previous line was {previous_line} with home/away probabilities of {previous_home_prob}/{previous_away_prob}.<br>\
                    Opening line was {opening_line} with home/away probabilities of {opening_home_prob}/{opening_away_prob}.<br>\
                    </p>"
            else: # Spread
                # Filter the df to just the columns I need
                nflodds_sub3 = nflodds_sub2[['currentdate', 'currenthour', 'home_odds', 'away_odds', 'home_points']]
                # Ensure the home_odds, away_odds, and home_points columns are numeric
                nflodds_sub3['home_odds'] = pd.to_numeric(nflodds_sub3['home_odds'])
                nflodds_sub3['away_odds'] = pd.to_numeric(nflodds_sub3['away_odds'])
                nflodds_sub3['home_points'] = pd.to_numeric(nflodds_sub3['home_points'])    
                # Convert all the odds columns to probabilities
                nflodds_sub3['home_prob'] = nflodds_sub3['home_odds'].apply(decimal2ProbabilityConverter)
                nflodds_sub3['away_prob'] = nflodds_sub3['away_odds'].apply(decimal2ProbabilityConverter)
                # Group the data by website and hour of currenttime
                nflodds_grouped = nflodds_sub3.groupby(['currentdate', 'currenthour']).mean()
                # Reset the index and sort nflodds_grouped
                nflodds_grouped.reset_index(inplace = True)
                nflodds_grouped.sort_values(by = ['currentdate', 'currenthour'], 
                                            ascending = False, inplace = True)
                nflodds_grouped.reset_index(drop = True, inplace = True)
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
                # Convert all the prob columns to American odds
                opening_home_prob = probability2AmericanConverter(opening_home_prob)
                previous_home_prob = probability2AmericanConverter(previous_home_prob)
                current_home_prob = probability2AmericanConverter(current_home_prob)
                opening_away_prob = probability2AmericanConverter(opening_away_prob)
                previous_away_prob = probability2AmericanConverter(previous_away_prob)
                current_away_prob = probability2AmericanConverter(current_away_prob)
                # Round all points and probabilities to nearest .5 or whole number
                opening_line = myround(opening_line, decimal = .25)
                current_line = myround(current_line, decimal = .25)
                previous_line = myround(previous_line, decimal = .25)
                line_difference = myround(line_difference, decimal = .25)
                # If the consenus line has moved by .5, we should add this to the message
                if abs(current_line - previous_line) >= 0.25:
                    # Add the movement to the message if the line moves by .5 points or the home/away odds move by .5 probability
                    spread_message += f"<p>The Spread for <b>{home_team}</b> vs. <b>{away_team}</b> on {commencetimelong} has moved by {line_difference}.<br>\
                    Current line is {current_line} with home/away probabilities of {current_home_prob}/{current_away_prob}.<br>\
                    Previous line was {previous_line} with home/away probabilities of {previous_home_prob}/{previous_away_prob}.<br>\
                    Opening line was {opening_line} with home/away probabilities of {opening_home_prob}/{opening_away_prob}.<br>\
                    </p>"

    # Format the spread and ou message if they are empty
    spread_message = "There have been no significant movements since last pull." if len(spread_message) == 0 else spread_message
    ou_message = "There have been no significant movements since last pull." if len(ou_message) == 0 else ou_message
    
    # Start the HTML version of your message
    html_email_message = f"""\
    <html>
      <body>
        <h2>NFL Week {NFL_Week}</h2>
        <h3>Spread Movements</h3>
        <p>{spread_message}</p>
        <h3>O/U Movements</h3>
        <p>{ou_message}</p>
      </body>
    </html>
    """
    
    # Add HTML/plain-text parts to MIMEMultipart message
    message.attach(MIMEText(html_email_message, "html"))
    
    # Email recipient list
    email_list = ["loudoun5@yahoo.com", "dangeloreategui@gmail.com"]
            
    # Create secure connection with server and send email
    context = ssl.create_default_context()
    
    for receivier_email in email_list:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message.as_string())
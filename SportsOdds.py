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

def findGameID(HomeTeam, CommenceTimeShort):
   try:
        connection = psycopg2.connect(user = "postgres",
                                      password = "RfC93TiD!ab",
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
        connection = psycopg2.connect(user = "postgres",
                                      password = "RfC93TiD!ab",
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
        connection = psycopg2.connect(user = "postgres",
                                      password = "RfC93TiD!ab",
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
        connection = psycopg2.connect(user = "postgres",
                                      password = "RfC93TiD!ab",
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
        
def data_download_logging(table_name, current_date, current_time):
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
        sql_insert_query = f"INSERT INTO data_download_logs (data_table_name, curr_date, curr_time) \
        VALUES ({table_name}, $${current_date}$$, $${current_time}$$)"
        cursor.execute(sql_insert_query)
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
    
    # Send download log to data_download_logs
    data_download_logging('nflodds', CurrentDate, CurrentTime)
    
    message = client.messages.create(
                         body=f"NFL odds were downloaded on {CurrentDate} at {CurrentTime}. You have {requests_remaining} requests remaining.",
                         from_='+12562911093',
                         to='+15712718265')
    
    
    
    




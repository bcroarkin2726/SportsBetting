# -*- coding: utf-8 -*-
"""
Created on Fri Dec 13 10:21:03 2019

@author: Brandon Croarkin
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import psycopg2
import os
import sys
from datetime import datetime
from twilio.rest import Client
sys.path.append(os.path.dirname(os.path.abspath('config.py')) + '\\Documents\\GitHub\\SportsBetting')
import config

########################### Custom Functions ##################################

def findGameID(NFL_Week, Home_Team, Away_Team):
    """
    @NFL_Week the NFL week of the game being played (e.g. 15)
    @Home_Team the home team in the game
    @Away_Team the away team in the game
    Uses the NFL_Week of the game and the names of the teams involved to 
    find the gameid in the nflgames table.
    """
    try:
        connection = psycopg2.connect(user = config.psycopg2_username,
                                      password = config.psycopg2_password,
                                      host = "127.0.0.1",
                                      port = "5432",
                                      database = "SportsBetting")
        cursor = connection.cursor()
        # Search for game id using fields input
        sql_select_query = f"SELECT gameid FROM nflgames WHERE nfl_week = {NFL_Week} \
        AND hometeam = $${Home_Team}$$ AND awayteam = $${Away_Team}$$"
        cursor.execute(sql_select_query)
        results = cursor.fetchone()[0]
        return(results)
    except (Exception, psycopg2.Error) as error:
       print("Error in operation", error)
    finally:
       # closing database connection.
       if (connection):
           cursor.close()
           connection.close()

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

############################ 538 Web Scrape ###################################

# Scrape the 538 website
five38_url = 'https://projects.fivethirtyeight.com/2019-nfl-predictions/games/?ex_cid=rrpromo'
# Web scrape FiveThirtyEight for relevant information
response = requests.get(five38_url)
soup = BeautifulSoup(response.text, "html.parser")

games = list(list(list(list(list(list(soup)[1])[1])[4])[2])[1])
upcoming = list(games[0])
upcoming_soup = BeautifulSoup(str(upcoming), "html.parser")
upcoming_list = list(upcoming_soup.find_all('td'))

# Create an empty dataframe to append data to
five38_odds = pd.DataFrame(columns = ['NFL_WEEK', 'PLAYER', 'TEAM', \
                            'PROP', 'BOVADA_LINE', 'OVER_ODDS', 'IMPLIED_OVER_PROBABILITY', \
                            'UNDER_ODDS', 'IMPLIED_UNDER_PROBABILITY', 'FP_PROJECTION'])

## Test loop to extract data from upcoming_list
#for item in upcoming_list:
#    output_class = ' '.join(item['class'])
#    text = item.get_text()
#    game_date = item.parent.parent.parent.parent.parent.parent.find('h4').get_text()
#    if output_class == 'td logo':
#        print('\n')
#    else:
#        print('Output class:', output_class, 'Text:', text, 'Game Date:', game_date)

# Map the list structure to the class for each item
class_dictionary = {0: 'Away Logo',
                    1: 'Away Team',
                    2: 'N/A', # The away spread, but this field is empty
                    3: 'Away Win Probability',
                    4: 'Away Score',
                    5: 'Home Logo',
                    6: 'Home Team',
                    7: 'Home Spread',
                    8: 'Home Win Probability',
                    9: 'Home Score'
        }

# Create a lookup dictionary for teams
team_dictionary = {'Baltimore': 'Baltimore Ravens',
                   'Green Bay': 'Green Bay Packers',
                   'Houston': 'Houston Texans',
                   'Kansas City': 'Kansas City Chiefs',
                   'Seattle': 'Seattle Seahawks',
                   'Tampa Bay': 'Tampa Bay Buccaneers',
                   'Tennessee': 'Tennessee Titans',
                   'Miami': 'Miami Dolphins',
                   'New England': 'New England Patriots',
                   'N.Y. Giants': 'New York Giants',
                   'N.Y. Jets': 'New York Jets',
                   'Philadelphia': 'Philadelphia Eagles',
                   'Chicago': 'Chicago Bears',
                   'Cincinnati': 'Cincinnati Bengals',
                   'Washington': 'Washington Redskins',
                   'Carolina': 'Carolina Panthers',
                   'Denver': 'Denver Broncos',
                   'Detroit': 'Detroit Lions',
                   'Arizona': 'Arizona Cardinals',
                   
        }


# Set year variable
Year = 2019

for num, item in enumerate(upcoming_list):
    # if this item is greater than 0 and divisible by 10, this signifies the
    # end to the stats collected for a game and we can upload to postgres
    if (num > 0) & (num % 10 == 0):
        # Find the date of the game
        game_date = item.parent.parent.parent.parent.parent.parent.find('h4').get_text()
        # Find the NFL Week of the game
        NFL_Week = findNFLWeek(datetime.strptime(game_date, "%A, %b. %d").strftime(f'%m/%d/{Year}'))
        # Find the gameid of this game
        gameid = findGameID(NFL_Week, HomeTeam, AwayTeam)
        # Find the CurrentDate and CurrentTime
        d = datetime.today()
        CurrentDate = d.strftime('%m/%d/%Y')
        CurrentTime = d.strftime('%H:%M:%S')
        # Upload to postgres with all the variables for spread
        insertNFLOdds(gameid, CurrentDate, CurrentTime, 'FiveThirtyEight', 'Spread', 1.952, 1.952, HomePoints, AwayPoints)
        # Upload to postgres with all the variables for spread
        insertNFLOdds(gameid, CurrentDate, CurrentTime, 'FiveThirtyEight', 'Moneyline', HomeOdds, AwayOdds, 0, 0)
    else:
        # We can skip over most of the list items as they are unneeded or duplicative
        if num % 10 in [0, 2, 3, 4, 5, 9]:
            continue
        else:
            if num % 10 == 1:
                # Away Team
                AwayTeam = x
            elif num % 10 == 6:
                # Home Team
                HomeTeam = item.get_text().strip()
            elif num % 10 == 7:
                # Home and Away Spread
                HomePoints = x
                AwayPoints = x
            elif num % 10 == 8:
                # Home and Away Probability
                HomeOdds = x
                AwayOdds = x
                            


# -*- coding: utf-8 -*-
"""
Created on Fri Dec 13 10:21:03 2019

@author: Brandon Croarkin
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import sys
from datetime import datetime
sys.path.append(os.path.dirname(os.path.abspath('config.py')) + '\\Documents\\GitHub\\SportsBetting')
import config

########################### Custom Functions ##################################

def home2AwaySpread(home_spread):
    """
    @home_spread the spread listed for the home team on FiveThirtyEight 
    Takes the home spread and converts it to the away spread.
    Ex: -5 --> +5 
    """
    if home_spread[0] == '-':
        return(home_spread.replace('-','+'))
    else:
        return(home_spread.replace('+','-'))
        
def home2AwayWinProbability(home_win_probability):
    """
    @home_win_probability the win probability listed for the home team on 
    FiveThirtyEight
    Takes the home win probability and converts it to the away win probability
    Ex: 68% --> 32%
    """
    home_win_probability = float(home_win_probability.replace('%',''))
    return(str(round(100 - home_win_probability)) + '%')

def probability2DecimalConverter(win_probability):
    """
    @win_probability the percent odds for a team to win a game in decimal
    format (ex. .652)
    This function takes in win probability and converts it to the American odds
    Ex: .65 --> 1.54
    """
    # Remove any percentage symbols if there and convert to float if not already
    if type(win_probability) == str:
        win_probability = win_probability.replace('%','')
        win_probability = float(win_probability)
        
    # Need to convert the win probabilty to a 0-1 scale if not already
    if (win_probability >= 1) & (win_probability < 100):
        win_probability = win_probability / 100
    elif (win_probability > 0) & (win_probability < 1):
        pass
    else:
        print("bad win probability")
        
    # Convert the win probability to the decimal odd   
    return(round(1/win_probability,2))

def findGameID(Home_Team, NFL_Week = 0, CommenceTimeShort = 0):
    """
    @Home_Team the home team in the game (the only truly required field)
    @NFL_Week the NFL week of the game being played (e.g. 15)
    @CommenceTimeShort the date of the game (e.g. 11/21/2019)
    If the CommenceTimeShort is provided, we can use the name of the home team
    and the CommenceTimeShort to find the GameID. Otherwise, we need to use 
    the NFL_Week of the game and the names of the teams involved to 
    find the GameID in the nflgames table.
    """
    # If CommenceTimeShort is provided, we can use that and Home_Team to
    # find the GameID
    if CommenceTimeShort != 0:
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
    
    # Without the CommenceTimeShort, we need to use the NFL Week and Home_Team
    # to find the GameID
    elif NFL_Week != 0:
        try:
            connection = psycopg2.connect(user = config.psycopg2_username,
                                          password = config.psycopg2_password,
                                          host = "127.0.0.1",
                                          port = "5432",
                                          database = "SportsBetting")
            cursor = connection.cursor()
            # Search for game id using fields input
            sql_select_query = f"SELECT gameid FROM nflgames WHERE nfl_week = {NFL_Week} \
            AND hometeam = $${Home_Team}$$"
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
    
    # Without either the CommenceTimeShort or Home_Team, we do not have enough
    # information to return a GameID
    else:
        return('Not enough information provided.')

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

# Set year variable
Year = 2021

# Scrape the 538 website
five38_url = f'https://projects.fivethirtyeight.com/{Year}-nfl-predictions/games/?ex_cid=rrpromo'
# Web scrape FiveThirtyEight for relevant information
response = requests.get(five38_url)
soup = BeautifulSoup(response.text, "html.parser")
print(soup)

games = list(list(list(list(list(list(soup)[1])[1])[4])[2])[1])
upcoming = list(games[0])
upcoming_soup = BeautifulSoup(str(upcoming), "html.parser")
upcoming_list = list(upcoming_soup.find_all('td'))

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
team_dictionary = {'Atlanta': 'Atlanta Falcons',
                   'Arizona': 'Arizona Cardinals',
                   'Baltimore': 'Baltimore Ravens',
                   'Buffalo': 'Buffalo Bills',
                   'Carolina': 'Carolina Panthers',
                   'Chicago': 'Chicago Bears',
                   'Cincinnati': 'Cincinnati Bengals',
                   'Cleveland': 'Cleveland Browns',
                   'Dallas': 'Dallas Cowboys', 
                   'Denver': 'Denver Broncos',
                   'Detroit': 'Detroit Lions',
                   'Green Bay': 'Green Bay Packers',
                   'Houston': 'Houston Texans',
                   'Indianapolis': 'Indianapolis Colts',
                   'Jacksonville': 'Jacksonville Jaguars',
                   'Kansas City': 'Kansas City Chiefs',
                   'L.A. Chargers': 'Los Angeles Chargers',
                   'L.A. Rams': 'Los Angeles Rams',
                   'Miami': 'Miami Dolphins',
                   'Minnesota': 'Minnesota Vikings',
                   'New England': 'New England Patriots',
                   'New Orleans': 'New Orleans Saints',
                   'N.Y. Giants': 'New York Giants',
                   'N.Y. Jets': 'New York Jets',
                   'Oakland': 'Oakland Raiders',
                   'Philadelphia': 'Philadelphia Eagles',
                   'Pittsburgh': 'Pittsburgh Steelers',
                   'San Francisco': 'San Francisco 49ers',
                   'Seattle': 'Seattle Seahawks',
                   'Tampa Bay': 'Tampa Bay Buccaneers',
                   'Tennessee': 'Tennessee Titans',
                   'Washington': 'Washington Redskins',                   
        }

for num, item in enumerate(upcoming_list[:81]):
    print(num)
    # if this item is greater than 0 and divisible by 10, this signifies the
    # end to the stats collected for a game and we can upload to postgres
    if (num > 0) & (num % 10 == 0):
        # Find the date of the game
        game_date = item.parent.parent.parent.parent.parent.parent.find('h4').get_text()
        # Find the NFL Week of the game
        NFL_Week = findNFLWeek(datetime.strptime(game_date, "%A, %b. %d").strftime(f'%m/%d/{Year}'))
        # Convert HomeTeam and AwayTeam to full names
        HomeTeam = team_dictionary[HomeTeam]
        AwayTeam = team_dictionary[AwayTeam]
        # Ensure CommenceTimeShort is 0, so it doesn't interfere
        CommenceTimeShort = 0
        # Find the gameid of this game
        gameid = findGameID(HomeTeam, NFL_Week = NFL_Week)
        # Find the CurrentDate and CurrentTime
        d = datetime.today()
        CurrentDate = d.strftime('%m/%d/%Y')
        CurrentTime = d.strftime('%H:%M:%S')
        # Convert the Home and Away Points to floats
        HomePoints = float(HomePoints.replace('+',''))
        AwayPoints = float(AwayPoints.replace('+',''))
        # Convert the Home and Away Odds to Decimal Odds
        HomeOdds = probability2DecimalConverter(HomeOdds)
        AwayOdds = probability2DecimalConverter(AwayOdds)
        # Print the results to test
        print(game_date, gameid, NFL_Week, HomeTeam, AwayTeam, HomePoints, AwayPoints, HomeOdds, AwayOdds)
#        # Upload to postgres with all the variables for spread
#        insertNFLOdds(gameid, CurrentDate, CurrentTime, 'FiveThirtyEight', 'Spread', 1.91, 1.91, HomePoints, AwayPoints)
#        # Upload to postgres with all the variables for moneyline
#        insertNFLOdds(gameid, CurrentDate, CurrentTime, 'FiveThirtyEight', 'Moneyline', HomeOdds, AwayOdds, 0, 0)
    else:
        # We can skip over most of the list items as they are unneeded or duplicative
        if num % 10 in [0, 3, 4, 5, 9]:
            continue
        else:
            if num % 10 == 1:
                # Away Team
                AwayTeam = item.get_text().strip()
            elif num % 10 == 2:
                # Away Team Spread
                value = item.get_text().strip()
                if value == '':
                    continue
                else:
                    # Home and Away Spread
                    HomePoints = item.get_text().strip()
                    AwayPoints = home2AwaySpread(HomePoints)
            elif num % 10 == 6:
                # Home Team
                HomeTeam = item.get_text().strip()
            elif num % 10 == 7:
                # Home Team Spread
                value = item.get_text().strip()
                if value == '':
                    continue
                else:
                    # Home and Away Spread
                    HomePoints = item.get_text().strip()
                    AwayPoints = home2AwaySpread(HomePoints)
            elif num % 10 == 8:
                # Home and Away Probability
                HomeOdds = item.get_text().strip()
                AwayOdds = home2AwayWinProbability(HomeOdds)
                            


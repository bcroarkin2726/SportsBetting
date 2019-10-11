# -*- coding: utf-8 -*-
"""
Created on Tue Oct  1 10:35:39 2019

@author: Brandon Croarkin
"""

import psycopg2
import pandas as pd

############################## HELPER FUNCTIONS ###############################
def myround(x, base = 0.5):
    return base * round(x/base)

############################ READING/PULLING DATA #############################

# Read in data from PostgreSQl
try:
    connection = psycopg2.connect(user = "postgres",
                                  password = "RfC93TiD!ab",
                                  host = "127.0.0.1",
                                  port = "5432",
                                  database = "SportsBetting")
    cursor = connection.cursor()
    # Check if row already exists
    sql_select_query = f"SELECT * FROM nflodds"
    cursor.execute(sql_select_query)
    nflodds = cursor.fetchall()
except (Exception, psycopg2.Error) as error:
    print("Error in update operation", error)
finally:
    # closing database connection.
    if (connection):
        cursor.close()
        connection.close()

# Convert data pull to a pandas dataframe
nflodds_df = pd.DataFrame(nflodds, columns = ['NFLOddsID', 'GameID', 'CurrentDate', 'CurrentTime',
                                              'Website', 'BetType', 'HomeOdds', 'AwayOdds',
                                              'HomePoints', 'AwayPoints'])

# Convert the HomeOdds, AwayOdds, HomePoints, and AwayPoints to float 
nflodds_df['HomeOdds'] = pd.to_numeric(nflodds_df['HomeOdds'])
nflodds_df['AwayOdds'] = pd.to_numeric(nflodds_df['AwayOdds'])
nflodds_df['HomePoints'] = pd.to_numeric(nflodds_df['HomePoints'])
nflodds_df['AwayPoints'] = pd.to_numeric(nflodds_df['AwayPoints'])

# Read in nfl game data from PostgreSQl
try:
    connection = psycopg2.connect(user = "postgres",
                                  password = "RfC93TiD!ab",
                                  host = "127.0.0.1",
                                  port = "5432",
                                  database = "SportsBetting")
    cursor = connection.cursor()
    # Check if row already exists
    sql_select_query = f"SELECT * FROM nflgames"
    cursor.execute(sql_select_query)
    nflgames = cursor.fetchall()
except (Exception, psycopg2.Error) as error:
    print("Error in update operation", error)
finally:
    # closing database connection.
    if (connection):
        cursor.close()
        connection.close()

# Convert data pull to a pandas dataframe
nflgames_df = pd.DataFrame(nflgames, columns = ['GameID', 'CommenceTimeLong', 'CommenceTimeShort',
                                              'NFL_Week', 'AwayTeam', 'HomeTeam'])

############################## ANALYSIS #######################################    

##### Group by and aggregate to answer key questions   

### Question 1 = what are the current odds for the day across games?
nflodds_df[nflodds_df['CurrentDate'] == max(nflodds_df['CurrentDate'])].groupby(['GameID', 'BetType', 'CurrentDate'])['HomeOdds', 'AwayOdds', 'HomePoints', 'AwayPoints'].mean()

### Question 2 = how do Bovada odds today compare to the average?
bovada_odds = nflodds_df[(nflodds_df['CurrentDate'] == max(nflodds_df['CurrentDate'])) & (nflodds_df['Website'] == 'Bovada')].groupby(['GameID', 'BetType'])['HomeOdds', 'HomePoints'].mean()
average_home_odds = nflodds_df[nflodds_df['CurrentDate'] == max(nflodds_df['CurrentDate'])].groupby(['GameID', 'BetType'])['HomeOdds', 'HomePoints'].mean()
odds_comparison = bovada_odds.merge(average_home_odds, left_index = True, right_index = True)
odds_comparison.columns = ['Bovada_HomeOdds', 'Bovada_HomePoints', 'Industry_HomeOdds', 'Industry_HomePoints']

### Question 3 = how have the odds moved across the week?
odds_movements = nflodds_df[nflodds_df['BetType'] == 'Spread'].groupby(['GameID', 'CurrentDate'])['HomeOdds'].mean()
odds_movements = odds_movements.reset_index()
odds_movements = odds_movements.pivot(index = odds_movements['GameID'], columns = 'CurrentDate')['HomeOdds']
totals_movements = nflodds_df[nflodds_df['BetType'] == 'O/U'].groupby(['GameID', 'CurrentDate'])['HomePoints'].mean()
totals_movements = totals_movements.reset_index()
totals_movements = totals_movements.pivot(index = totals_movements['GameID'], columns = 'CurrentDate')['HomePoints']
spread_movements = nflodds_df[nflodds_df['BetType'] == 'Spread'].groupby(['GameID', 'CurrentDate'])['HomePoints'].mean()
spread_movements = spread_movements.reset_index()
spread_movements = spread_movements.pivot(index = spread_movements['GameID'], columns = 'CurrentDate')['HomePoints']

### Question 4 - What are the implied team totals for each game?

# Get the current average totals for each game
home_totals = average_home_odds.reset_index()
home_totals = home_totals[home_totals['BetType'] == 'O/U']
home_totals = home_totals[['GameID', 'HomePoints']]
home_totals.set_index('GameID', inplace = True)

# Get the current average spreads for each game
home_spreads = average_home_odds.reset_index()
home_spreads = home_spreads[home_spreads['BetType'] == 'Spread']
home_spreads = home_spreads[['GameID', 'HomePoints']]
home_spreads.set_index('GameID', inplace = True)

# Combine and format the tables
implied_points = home_totals.merge(home_spreads, left_index = True, right_index = True)
implied_points.columns = ['TotalPoints', 'Spread']

# Derive the home and team implied points
implied_points['HomePoints'] = myround(implied_points['TotalPoints']/2 + implied_points['Spread']/2)
implied_points['AwayPoints'] = myround(implied_points['TotalPoints']/2 - implied_points['Spread']/2)

# Merge with nflgames_df to get the names of the home and away team
GameTeams = nflgames_df[['GameID', 'NFL_Week', 'HomeTeam', 'AwayTeam']].set_index('GameID')
implied_points = implied_points.merge(GameTeams, left_index = True, right_index = True)[['NFL_Week', 'HomePoints', 'AwayPoints', 'HomeTeam', 'AwayTeam']]
home_implied_points = implied_points[['HomePoints', 'HomeTeam']]
home_implied_points.columns = ['ImpliedPoints', 'Team']
home_implied_points.set_index('Team', inplace = True)
away_implied_points = implied_points[['AwayPoints', 'AwayTeam']]
away_implied_points.columns = ['ImpliedPoints', 'Team']
away_implied_points.set_index('Team', inplace = True)

implied_points = home_implied_points.append(away_implied_points).sort_values(by = ['ImpliedPoints'],
                                           ascending = False)



# -*- coding: utf-8 -*-
"""
Created on Wed Nov 20 11:26:04 2019

@author: Brandon Croarkin
"""

import psycopg2
import pandas as pd
from datetime import datetime 
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath('config.py')) + '\\Documents\\GitHub\\SportsBetting')
import config

############################ Twilio Connection ################################

# Download the helper library from https://www.twilio.com/docs/python/install
from twilio.rest import Client

# Connect to Twilio
client = Client(config.account_sid, config.auth_token)

########################### Custom Functions ##################################

def pullDailyDownloads(CurrentDate):
   try:
        connection = psycopg2.connect(user = "ardi",
                                      password = "bofa",
                                      database = "BOFABET")
        cursor = connection.cursor()
        # Check if row already exists
        sql_select_query = f"SELECT * FROM data_download_logs WHERE curr_date = $${CurrentDate}$$"       
        cursor.execute(sql_select_query)
        results = cursor.fetchall()
        return(results)
   except (Exception, psycopg2.Error) as error:
       print("Error in update operation", error)
   finally:
       # closing database connection.
       if (connection):
           cursor.close()
           connection.close()

# We are getting the stats for today
CurrentDate = datetime.now().strftime("%m/%d/%Y")
CurrentTime = datetime.now().strftime('%H:%M:%S')

# Pull today's downloads into a single pandas dataframe
daily_downloads = pd.DataFrame(pullDailyDownloads(CurrentDate), 
                               columns = ['Data_Table_Name', 'Current_Date', 'Current_Time', 'Requests_Remaining'])

# Get the number of pulls and requests remaining for nfl_odds
nfl_odds_downloads = len(daily_downloads[daily_downloads['Data_Table_Name'] == 'nflodds'])
requests_remaining = daily_downloads.sort_values(by = ['Current_Time'], ascending = False).head(1)['Requests_Remaining']

# Get the number of pulls for Bovada prop comparisons (this encompasses player statistics and player projections)
bovada_props_downloads = len(daily_downloads[daily_downloads['Data_Table_Name'] == 'bovada_props'])

# Send out a text message with the daily download summary.
message = client.messages.create(
             body=f"Today is {CurrentDate}. \
             NFL odds were downloaded {nfl_odds_downloads} times today.\
             You have {requests_remaining} requests remaining.\
             Bovada player props were downloaded {bovada_props_downloads} times",
             from_='+12562911093',
             to='+15712718265')




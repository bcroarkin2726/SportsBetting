# -*- coding: utf-8 -*-
"""
Created on Wed Dec  4 16:17:23 2019

@author: Brandon Croarkin
"""

import smtplib, ssl
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath('config.py')) + '\\Documents\\GitHub\\SportsBetting')
import config

port = 465  # For SSL
password = config.gmail_password

# Create a secure SSL context
context = ssl.create_default_context()

# Email here
sender_email = "bofabet677@gmail.com"
receiver_email = "loudoun5@yahoo.com"
message = """\
Subject: Hi there

This message is sent from Python."""

with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:
    server.login("bofabet677@gmail.com", password)
    server.sendmail(sender_email, receiver_email, message)



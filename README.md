#### Created at the NANOG 70 Hackathon

# Manage Maintenance

Created by Colin McIntosh & [Mattijs Jonker](https://github.com/mattijsjonker)


## Overview

This is a tool used to create Google Calendar events from maintenance
notification emails.

## Things to know
* You need to configure a Google account that can create calendar events
  with OAuth2. See the directions below.
* The maintenance notification emails are read via IMAP. You'll need to
  configure IMAP using the instructions below.


## Google Calendar access through Python
Follow steps @ https://developers.google.com/google-apps/calendar/quickstart/python

1. Enable calendar widget:
http://quehow.com/how-to-enable-google-calendar-in-gmail/7881.html

2. Install Python API bindings
pip install --user google-api-python-client

3. Enable calendar API and setup credentials for external access
https://console.developers.google.com/start/api?id=calendar

4. Try Quickstart example
n.b.: set scope to write access (i.e., "https://www.googleapis.com/auth/calendar" without the ".readonly" suffix)

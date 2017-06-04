#!/usr/bin/env python3
from __future__ import print_function
import errno
import httplib2
import os
from datetime import datetime, timedelta, date
import dateutil.parser
import logging
import argparse
from imp import reload
from apiclient import discovery
from apiclient import errors
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

SCOPES                  = "https://www.googleapis.com/auth/calendar"
APPLICATION_NAME        = "Google Calendar API Python Quickstart"

# Home directory for config files, etc.
HOME_DIR                = os.path.expanduser("~")

# Directory for secret file and in which the OAuth credentials file will be created
CREDENTIALS_DIR         = os.path.join(HOME_DIR, ".credentials")
CLIENT_SECRET_FILE      = os.path.join(CREDENTIALS_DIR, "client_secret.json")
CREDENTIALS_FILENAME    = "oauth_creds.json" # n.b.: no path

LOGGING_FILE            = os.path.join(HOME_DIR, "hackathon_debug.log")


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def get_client_secret_file_path():
    current_dir = os.path.dirname(os.path.realpath(__file__))
    clients_secrets_path = os.path.join(current_dir, "..", "client_secret.json")
    return clients_secrets_path


class GoogleCalendar(object):
    """ Google Calendar API Wrapper Class """

    def __init__(self):

        try:
            self._flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
            # Prevent a browser from opening
            self._flags.noauth_local_webserver = True
        except ImportError:
            self._flags = None

        ## Init logging
        self._logger = self.create_logger(logging_filename=LOGGING_FILE)
        logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)

        ## Get credentials, build calendar service object
        mkdir_p(CREDENTIALS_DIR)
        credentials = self.get_credentials(CLIENT_SECRET_FILE, SCOPES, CREDENTIALS_DIR, CREDENTIALS_FILENAME)
        self._service = self.get_service(credentials)


        self.naive_find_event_overlap()

    def create_logger(self, logging_filename):

        ## Setup logging
        reload(logging)
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)

        # File and console handlers
        fhandler_dbg = logging.FileHandler(filename=logging_filename, mode='w')
        fhandler_dbg.setLevel(logging.DEBUG)
        chandler = logging.StreamHandler()
        chandler.setLevel(logging.DEBUG)

        # Create formatter
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s [%(process)d:%(thread)d]")

        # Add formatter to handlers
        fhandler_dbg.setFormatter(formatter)
        chandler.setFormatter(formatter)

        # Add handlers to logger
        logger.addHandler(fhandler_dbg)
        logger.addHandler(chandler)

        return logger

    # Create credentials directory, if necessary
    def get_credentials(self, client_secret_file, scopes, credentials_dir, credentials_file, flags=None):

        # Create credentials folder, if necessary
        if not os.path.exists(credentials_dir):
            os.makedirs(credentials_dir)

        # Store for credentials file
        credential_path = os.path.join(credentials_dir, credentials_file)
        store = Storage(credential_path)
        credentials = store.get()

        if not credentials or credentials.invalid:
            flow = client.flow_from_clientsecrets(client_secret_file, scopes)
            flow.user_agent = APPLICATION_NAME
            if self._flags:
                credentials = tools.run_flow(flow, store, self._flags)
            else: # Needed only for compatibility with Python 2.6
                credentials = tools.run(flow, store)
            self._logger.debug("Storing credentials to '{}'".format(credential_path))
        else:
            self._logger.debug("Got valid credential from '{}'".format(credential_path))

        return credentials

    # Create a Google Calendar API service object
    def get_service(self, credentials):
        http = credentials.authorize(httplib2.Http())
        service = discovery.build('calendar', 'v3', http=http)
        self._logger.debug("Created service object")

        return service

    # Create a calendar event for a given calendar ID
    def create_calendar_event(self, event, calendarId='primary'):
        # Create event
        try:
            event = self._service.events().insert(calendarId=calendarId, body=event).execute()
            self._logger.info("Event created: '{}'".format(event.get('htmlLink')))
            return event
        except errors.HttpError as e:
            self._logger.error("Exception while creating event: {}".format(str(e)))
            return

    # Update a calendar event for a given calendar ID and event ID
    def update_calendar_event(self, eventId, event, calendarId='primary'):
        # Update event
        try:
            event = self._service.events().update(eventId=eventId, calendarId=calendarId, body=event).execute()
            self._logger.info("Event updated: '{}'".format(event.get('htmlLink')))
            return event
        except errors.HttpError as e:
            self._logger.error("Exception while updating event: {}".format(str(e)))
            return

    # Delete a calendar event for a given calendar ID and event ID
    def delete_calendar_event(self, eventId, calendarId='primary'):
        # Delete event
        self._service.events().delete(calendarId=calendarId, eventId=eventId).execute()
        self._logger.info("Event deleted: '{}'".format(eventId))

    # Get a calendar event for a given calendar ID and event ID
    def get_calendar_event(self, eventId, calendarId='primary'):
        # Get event
        event = self._service.events().get(calendarId='primary', eventId=eventId).execute()
        self._logger.info("Got event: {}".format(event['summary']))
        return event

    # A helper method to check if an event ID exists for a given calendar ID
    def is_existing_event_id(self, eventId, calendarId='primary'):
        try:
            event = self._service.events().get(calendarId=calendarId, eventId=eventId).execute()
            self._logger.debug("Got event summary: {}".format(event['summary']))
            return True
        except errors.HttpError as he:
            if "Not Found" in str(he):
                return False
            else: # raise he as it may have a different cause
                raise he
 
    # Create a new maintenance event for a given start time, end time, summary, description, location, and calendar ID
    def create_maintenance_event(self, newEventId, start_time, end_time, event_summary, event_description, event_location, calendarId='primary'):

        # Check eventId existence
        if self.is_existing_event_id(newEventId, calendarId):
            self._logger.info("Event with ID {} exists.".format(newEventId))
            return self.get_calendar_event(eventId=newEventId, calendarId=calendarId)

        # cf. https://developers.google.com/google-apps/calendar/v3/reference/events
        newEventBody = {
            'id'            : newEventId,
            'summary'       : event_summary,
            'location'      : event_location,
            'description'   : event_description,
            'start'         : {
                'dateTime'  : start_time.isoformat(),
                'timeZone'  : 'Universal',
            },
            'end': {
                'dateTime'  : end_time.isoformat(),
                'timeZone'  : 'Universal',
            },
            'reminders': {
                'useDefault': True
            },
        }

        # Call generic helper
        return self.create_calendar_event(newEventBody, calendarId=calendarId)

    # A naive helper to check for overlapping events
    def naive_find_event_overlap(self, calendarId='primary', singleEvents=True):

        # Be verbose
        self._logger.info("Getting the upcoming events")

        # list events
        eventsResult = self._service.events().list(
                calendarId=calendarId, singleEvents=singleEvents
        ).execute()

        events = eventsResult.get('items', [])

        if not events:
            self._logger.info("No upcoming events found.")

        ## Check for overlapping events, naively
        # Iterate all n events
        for i_event1 in events:
            # Iterate all n events again
            for i_event2 in events:
                # For the n(n-1) events
                if i_event1['id'] != i_event2['id']:
                    
                    start1_dt = dateutil.parser.parse(i_event1['start'].get('dateTime'))
                    start2_dt = dateutil.parser.parse(i_event2['start'].get('dateTime'))
                    end1_dt   = dateutil.parser.parse(i_event1['end'].get('dateTime'))
                    end2_dt   = dateutil.parser.parse(i_event2['end'].get('dateTime'))

                    if ((start1_dt == start2_dt) or ((start1_dt > start2_dt and start1_dt <= end2_dt) or (start1_dt <= start2_dt and start2_dt <= end1_dt))):
                        self._logger.info("overlap1 date: {} - {}; event (ID: {}): '{}'".format(start1_dt, end1_dt, i_event1['id'], i_event1['summary']))
                        self._logger.info("overlap2 date: {} - {}; event (ID: {}): '{}'".format(start2_dt, end2_dt, i_event2['id'], i_event2['summary']))

if __name__ == '__main__':
    bla = GoogleCalendar()

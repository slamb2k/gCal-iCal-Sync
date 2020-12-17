#!/usr/bin/python

from __future__ import print_function
import httplib2
from dateutil.parser import parse
from dateutil.tz import gettz
import re
import hashlib
from time import sleep

from apiclient import discovery, errors
import oauth2client
from oauth2client import client
from oauth2client import tools
from oauth2client import file

import argparse
import config

def get_credentials():
  """ Gets credentials to access gCal API """

  store = oauth2client.file.Storage(config.credential_store)
  credentials = store.get()
  if not credentials or credentials.invalid:
    flow = client.flow_from_clientsecrets(config.client_secret, 
      'https://www.googleapis.com/auth/calendar')
    flow.user_agent = config.application
    parser = argparse.ArgumentParser(parents=[tools.argparser])
    flags = parser.parse_args()
    credentials = tools.run_flow(flow, store, flags)
    print('Storing credentials to ' + config.credential_store)
  return credentials

def get_calendar_service():
  """ Gets a service object to use to query gCal API """

  credentials = get_credentials()
  http = credentials.authorize(httplib2.Http())
  return discovery.build('calendar', 'v3', http=http)

def load_ical(url):
  """ Loads an iCal file from a URL and returns an events object """

  resp, content = httplib2.Http(timeout=None).request(url)
  assert(resp['status'] == '200')

  # Decode for processing
  content = content.decode("utf-8")

  # Translate the weird Microsoft UTC references to something more consistent
  content = content.replace("\"tzone://Microsoft/Utc\"", "UTC")

  events = {}

  for event in re.findall("BEGIN:VEVENT.*?END:VEVENT", content, re.M|re.I|re.DOTALL):
    summary = re.search("summary:(.*)", event, re.I).group(1)

    if summary is None:
      print("Couldn't find summary. Skipping event.\nEvent Data: %s" % (event))
      continue

    allday = re.search("X-MICROSOFT-CDO-ALLDAYEVENT:TRUE", event, re.I)
    isAllDay = allday is not None

    if isAllDay:
      startDateRegEx = "dtstart;VALUE=DATE:(?P<date>(.*))"
      endDateRegEx = "dtend;VALUE=DATE:(?P<date>(.*))"
    else:
      startDateRegEx = "dtstart;TZID=(?P<timezone>.*?):(?P<date>(.*))"
      endDateRegEx = "dtend;TZID=(?P<timezone>.*?):(?P<date>(.*))"
    
    start = re.search(startDateRegEx, event, re.I)

    if start is None:
      print("Couldn't find start date. Skipping event - %s" % (summary))
      continue

    end = re.search(endDateRegEx, event, re.I)

    if end is None:
      print("Couldn't find end date. Skipping event - %s" % (summary))
      continue

    # Get the timezone string
    start_timezone_string = "UTC"
    if "timezone" in start.groupdict() and start.group("timezone") != "UTC":
      start_timezone_string = config.default_timezone

    try:
      # Get the start date and clean up
      start_date_string = start.group("date").replace('Z','')

      # Parse the start date to a timezone aware date object
      parsed_start_date = parse(start_date_string)

      # Get the parsed/default timezone and apply it
      start_date_tz = gettz(start_timezone_string)
      parsed_start_date = parsed_start_date.replace(tzinfo=start_date_tz)
    except:
      print("Couldn't parse start date: %s. Skipping event - %s" % (start_date_string,summary))
      continue  

    # Get the timezone string
    end_timezone_string = "UTC"
    if "timezone" in end.groupdict() and end.group("timezone") != "UTC":
      end_timezone_string = config.default_timezone
    
    try:
      # Get the end date and clean up
      end_date_string = end.group("date").replace('Z','')

      # Parse the end date to a timezone aware date object
      parsed_end_date = parse(end_date_string)

      # Get the parsed/default timezone and apply it
      end_date_tz = gettz(end_timezone_string)
      parsed_end_date = parsed_end_date.replace(tzinfo=end_date_tz)
    except:
      print("Couldn't parse end date: %s. Skipping event - %s" % (end_date_string,summary))
      continue  

    hash = hashlib.sha256(("%s %s %s" % (parsed_start_date.isoformat(), parsed_end_date.isoformat(), summary))
      .encode('utf-8')).hexdigest()

    # If the start date on the event is greater than the minimum start date then process
    if parsed_start_date.replace(tzinfo=None) >= parse(config.start_date):
      events[hash] = {
        'summary': summary,
        'start': {
          'dateTime': str(parsed_start_date).replace(' ','T'),
          'timeZone': start_timezone_string,
        },
        'end': {
          'dateTime': str(parsed_end_date).replace(' ','T'),
          'timeZone': end_timezone_string,
        },
        'id': hash
      }

  return events

def handle_existing_events(service, new_events):
  """ Examines existing gCal events and prunes as needed """

  if config.erase_all:
    print("Clearing calendar...")
    service.calendars().clear(calendarId=config.gcal_id).execute()

  for event in service.events().list(calendarId=config.gcal_id, maxResults=2500).execute()['items']:
    if event['id'] in new_events:
      del new_events[event['id']]
    elif config.remove_stale:
      print("Deleting stale event %s..." % (event['id'][0:8]))
      service.events().delete(calendarId=config.gcal_id, eventId=event['id']).execute()

def add_ical_to_gcal(service, events):
  """ Adds all events in event list to gCal """

  for i, event in enumerate(events):
    print("Adding %d/%d %s" % (i+1,len(events),events[event]['summary']))
    try:
      sleep(.3)
      service.events().insert(calendarId=config.gcal_id, body=events[event]).execute()
    except errors.HttpError as e:
      if e.resp.status == 409:
        print("Event already exists. Updating...")
        sleep(.3)
        service.events().update(calendarId=config.gcal_id, eventId=event, body=events[event]).execute()
        print("Event updated.")
      else:
        raise e

if __name__ == '__main__':
  new_events = load_ical(config.ical_url)
  service = get_calendar_service()
  handle_existing_events(service, new_events)
  add_ical_to_gcal(service, new_events)

# gCal-iCal-Sync

![Build Status](https://github.com/slamb2k/gCal-iCal-Sync/workflows/Build%20Status/badge.svg)

Syncs a public iCal URL to a Google Calendar. On each run, this program will add events to a Google calendar from an iCal (.ics) file provided as a URL. This can optionally remove all events from the calendar not found in the iCal file to create a Google calendar that is an exact copy of another available calendar.

# Installation

Assuming that you already have Python and pip installed correctly, you should be able to install required dependencies using:

    pip install -r requirements.txt

# Configuration

See config.example.py for an example configuration.

# Additional Notes

Google Calendar behaves a little weirdly when you attempt to remove existing events. This code accoomodates  deletion of existing/missing events and the entire calendar can be reset from the web interface. The problem is, the events are really just "hidden" and can be permanently removed by emptying the trash in the settings interface. 

More information can be found in the document above but I have still encountered **"Event already exists [409]"** when attempting to insert events after performing the additional steps mentioned in the [Delete an Event](https://support.google.com/calendar/answer/37113?co=GENIE.Platform%3DDesktop&hl=en) documentation. 
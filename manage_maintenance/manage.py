#!/usr/bin/env python3
# Copyright 2017 Netflix
import glob
import hashlib
import logging
import os
import re
import uuid
import yaml
from collections import namedtuple
from datetime import datetime

from manage_maintenance.google_calendar import GoogleCalendar
from manage_maintenance.imap import IMAP


LOG = logging.getLogger(__name__)


MaintenanceNotification = namedtuple("MaintenanceNotification", ("subject", "start_time", "end_time", "cid", "partner", "original_message"))


class ManageMaintenance(object):

    def __init__(self, imap_username, imap_password, imap_address, imap_folder, google_calendar_id=None):
        self._imap_username = imap_username
        self._imap_password = imap_password
        self._imap_addresss = imap_address
        self._imap_folder = imap_folder
        self.__imap_server = None
        self._notification_patterns = []
        self.load_notification_patterns()
        self._google_calendar_id = google_calendar_id
        self._google_calendar = GoogleCalendar()

    def _connect_to_imap(self):
        self.__imap_server = IMAP(username=self._imap_username, password=self._imap_password, address=self._imap_addresss)
        self.__imap_server.connect()

    @property
    def _imap(self):
        if not self.__imap_server:
            self._connect_to_imap()
        return self.__imap_server

    def load_notification_patterns(self):
        current_dir = os.path.dirname(os.path.realpath(__file__))
        patterns_directory = os.path.join(current_dir, "..", "notification_patterns", "*.yml")
        self._notification_patterns = []
        for file_path in glob.glob(patterns_directory):
            with open(file_path) as f:
                file_blob = f.read()
            patterns = yaml.load(file_blob)
            for pattern in patterns:
                self._notification_patterns.append(pattern)
        return

    def list_maintenances(self, since=None):
        since = since or datetime.now().strftime("%Y-%m-%d")
        email_ids = self._imap.list_message_ids_in_folder(folder_name=self._imap_folder, since=since)
        LOG.debug("Found %s emails in folder", len(email_ids))
        for email_id in email_ids:
            message = self._imap.get_message_by_id_from_folder(folder_name=self._imap_folder, email_id=email_id)
            msg_subject = message["Subject"]
            msg_from = message["From"].strip()

            for notification_config in self._notification_patterns:
                # Check email sender domain matches
                if notification_config.get("email_domain_pattern", None) and not re.search(notification_config["email_domain_pattern"], msg_from):
                    continue

                # Check email subject matches pattern
                if notification_config.get("email_subject_pattern", None) and not re.search(notification_config["email_subject_pattern"], msg_subject):
                    continue

                # Get important details
                cid, start_time, end_time, original_message = self._extract_info_from_message_naive(
                    message=message,
                    cid_pattern=notification_config["maintenance_cid_pattern"],
                    start_time_pattern=notification_config["maintenance_start_time_pattern"],
                    end_time_pattern=notification_config["maintenance_end_time_pattern"]
                )

                # Convert start_time and end_time to datetime objects
                if start_time:
                    start_time = datetime.strptime(start_time, notification_config["start_time_format"])
                if end_time:
                    end_time = datetime.strptime(end_time, notification_config["end_time_format"])

                # Yield each item
                if cid and start_time and end_time:
                    yield MaintenanceNotification(
                        subject=msg_subject,
                        start_time=start_time,
                        end_time=end_time,
                        cid=cid,
                        partner=notification_config["partner_name"],
                        original_message=original_message
                    )
                else:
                    LOG.warning("Missing one of CID, Start Time, or End Time: %s, %s, %s", cid, start_time, end_time)
        return

    def _extract_info_from_message_naive(self, message, cid_pattern, start_time_pattern, end_time_pattern):
        cid = None
        start_time = None
        end_time = None
        message_body = None
        for message_part in message.walk():
            # Get a message body if this message part has one
            if message_part.get_content_type() == "text/plain":
                message_body = message_part.get_payload(decode=True)
            elif message_part.get_content_type() == "text/html":
                message_body = message_part.get_payload(decode=True)
            else:
                continue    # We don't know how to parse this message part type

            if not message_body:
                continue    # The message part couldn't be decoded. Skip it.

            # Parse the message body
            message_body = str(message_body)
            match = re.search(cid_pattern, message_body, re.IGNORECASE)
            if match:
                cid = match.group(1)
            match = re.search(start_time_pattern, message_body, re.IGNORECASE)
            if match:
                start_time = match.group(1)
            match = re.search(end_time_pattern, message_body, re.IGNORECASE)
            if match:
                end_time = match.group(1)

            # If we have all of the things we need stop looking
            if cid and start_time and end_time:
                break
        return cid, start_time, end_time, message_body

    def _generate_maintenance_uuid(self, maintenance_notification):
        return hashlib.sha1(bytes("{}{}{}".format(
            maintenance_notification.cid,
            maintenance_notification.start_time.isoformat(),
            maintenance_notification.end_time.isoformat()
        ), "utf-8")).hexdigest()

    def add_maintenance_to_calendar(self, maintenance_notification):
        event_uuid = self._generate_maintenance_uuid(maintenance_notification)
        # event_uuid = str(uuid.uuid4()).replace("-", "")
        if not self._google_calendar.is_existing_event_id(eventId=event_uuid):
            self._google_calendar.create_maintenance_event(
                newEventId=event_uuid,
                start_time=maintenance_notification.start_time,
                end_time=maintenance_notification.end_time,
                event_summary="Scheduled Maintenance: {} {}".format(maintenance_notification.partner, maintenance_notification.cid),
                event_description="{} will be performing maintenance starting {} and ending {} that will affect the following CIDs:\n{}\n\n\n{}".format(
                    maintenance_notification.partner,
                    maintenance_notification.start_time.isoformat(),
                    maintenance_notification.end_time.isoformat(),
                    maintenance_notification.cid,
                    maintenance_notification.original_message
                ),
                event_location=""
            )

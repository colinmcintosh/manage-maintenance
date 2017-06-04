#!/usr/bin/env python3
# Copyright 2017 Netflix
import email
import imaplib
from datetime import datetime


class IMAP(object):
    """IMAP Server Wrapper Class."""

    def __init__(self, username, password, address):
        self._username = username
        self._password = password
        self._address = address
        self._imap = None

    def connect(self):
        self._imap = imaplib.IMAP4_SSL(self._address)
        return_code, data = self._imap.login(self._username, self._password)
        if return_code != "OK":
            raise Exception("Error logging in to IMAP as {}: {} {}".format(self._username, return_code, data))

    def list_message_ids_in_folder(self, folder_name, since=None):
        # Select the folder
        return_code, data = self._imap.select(folder_name)
        if return_code != "OK":
            raise Exception("Error selecting folder named '{}' via IMAP: {} {}".format(folder_name, return_code, data))

        # Build search query
        query = "SUBJECT \"NTT Communications\""
        if since:
            query += " SENTSINCE {}".format(since)

        # Get a list of message IDs in the folder
        return_code, data = self._imap.search(None, query)
        if return_code != "OK":
            raise Exception("No messages found in folder named '{}' via IMAP: {} {}".format(folder_name, return_code, data))

        mail_message_id_list = data[0].split(b" ")
        return mail_message_id_list

    def get_message_by_id_from_folder(self, folder_name, email_id):
        return_code, data = self._imap.fetch(email_id, '(RFC822)')
        if return_code != "OK":
            raise Exception("No message with ID {} found in folder named '{}' via IMAP: {} {}".format(email_id, folder_name, return_code, data))
        email_obj = email.message_from_bytes(data[0][1])
        return email_obj

#!/usr/bin/env python3
# Copyright 2017 Netflix
import logging
import os

from manage_maintenance.manage import ManageMaintenance


MAILBOX_FOLDER = "_OpenConnect/NetOps"


LOG = logging.getLogger(__name__)


def load_creds():
    with open(os.path.join(os.path.expanduser("~"), ".maintmanage")) as f:
        file_blob = f.read()
    cred_split = file_blob.split(":")
    return cred_split[0], cred_split[1]


def load_config_options_from_env():
    imap_address = os.getenv("IMAP_ADDRESS", None)
    imap_folder = os.getenv("IMAP_FOLDER", None)
    notification_patterns_folder = os.getenv("NOTIFICATION_PATTERNS_FOLDER", None)
    return imap_address, imap_folder, notification_patterns_folder


def main():
    logging.basicConfig(level=logging.INFO)
    username, password = load_creds()
    imap_address = 'imap.gmail.com'
    manager = ManageMaintenance(imap_username=username, imap_password=password, imap_address=imap_address, imap_folder=MAILBOX_FOLDER)
    for maintenance_notification in manager.list_maintenances(since="1-Oct-2017"):
        LOG.info("Adding maintenance event: {} {} {}".format(maintenance_notification.partner, maintenance_notification.cid, maintenance_notification.start_time))
        manager.add_maintenance_to_calendar(maintenance_notification=maintenance_notification)


if __name__ == "__main__":
    main()

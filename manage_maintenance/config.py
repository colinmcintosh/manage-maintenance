#!/usr/bin/env python3
# Copyright 2017 Netflix


class BaseConfig(object):

    SCHEDULE_FILE_PATH = "~/.manage-maintenance"
    SCHEDULE_FILE_NAME = "schedule.db"


class TestConfig(BaseConfig):

    SCHEDULE_FILE_PATH = "/tmp/manage-maintenance"


config = BaseConfig()

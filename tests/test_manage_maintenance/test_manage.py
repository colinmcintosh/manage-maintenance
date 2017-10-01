"""Test manage."""
import json
import os
import unittest
import pickle

from tinydb import TinyDB

import manage_maintenance.manage
from manage_maintenance.config import TestConfig
from manage_maintenance.manage import ManageMaintenance, MaintenanceNotification


class ManageMaintenanceTest(unittest.TestCase):
    """ManageMaintenance class test case."""

    def setUp(self):
        """Setup fake maintenance notification."""
        self._previous_config = manage_maintenance.manage.config
        manage_maintenance.manage.config = self.config = TestConfig()
        self.notification = MaintenanceNotification(subject="Yo stuff is goin' down!",
                                                    start_time="2017-12-01T01:00:00",
                                                    end_time="2017-12-01T02:00:00",
                                                    cid="ABC1234XYZ",
                                                    partner="Netflix",
                                                    original_message="Stuff is going down!")
        with self.db() as db:
            db.purge()

    def db(self):
        return TinyDB(os.path.join(self.config.SCHEDULE_FILE_PATH, self.config.SCHEDULE_FILE_NAME))

    def tearDown(self):
        manage_maintenance.manage.config = self._previous_config

    def test_add_to_schedule(self):
        """Test notification serialization."""
        ManageMaintenance.add_maintenance_to_schedule(self.notification)
        with self.db() as db:
            self.assertIn(self.notification._asdict(), db.all())


def main():
    """Main."""
    unittest.main()


if __name__ == '__main__':
    main()

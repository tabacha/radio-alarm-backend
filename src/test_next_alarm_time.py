#!/usr/bin/python3

from radio_common import get_next_alarm_time
from datetime import datetime
import unittest

class TestAlarmTime(unittest.TestCase):
    def test_inactive(self):
        alarmtime={
            "name": "Weckzeit 3",
            "time": "23:42",
            "active": False,
            "monday": True,
            "tuesday": True,
            "wednesday": True,
            "thursday": True,
            "friday": True,
            "saturday": False,
            "sunday": False,
            "once": False,
            "free": False,
            "not_free": False
        }
        rtn=get_next_alarm_time(alarm_time=alarmtime,start_dt=datetime.now)
        self.assertEqual(rtn, None)

    def test_next_monday(self):
        alarmtime={
            "name": "Weckzeit 3",
            "time": "23:42",
            "active": True,
            "monday": True,
            "tuesday": True,
            "wednesday": True,
            "thursday": True,
            "friday": True,
            "saturday": False,
            "sunday": False,
            "once": False,
            "free": False,
            "not_free": False
        }
        rtn=get_next_alarm_time(alarm_time=alarmtime,start_dt=datetime(year=2022,month=5,day=15,hour=8,minute=12))
        self.assertEqual(rtn.strftime("%Y-%m-%d %H:%M"),'2022-05-16 23:42')

    def test_next_friday(self):
        alarmtime={
            "name": "Weckzeit 3",
            "time": "23:42",
            "active": True,
            "monday": False,
            "tuesday": False,
            "wednesday": False,
            "thursday": False,
            "friday": True,
            "saturday": False,
            "sunday": False,
            "once": False,
            "free": False,
            "not_free": False
        }
        rtn=get_next_alarm_time(alarm_time=alarmtime,start_dt=datetime(year=2022,month=5,day=15,hour=8,minute=12))
        self.assertEqual(rtn.strftime("%Y-%m-%d %H:%M"),'2022-05-20 23:42')

    def test_same_day(self):
        alarmtime={
            "name": "Weckzeit 3",
            "time": "23:42",
            "active": True,
            "monday": False,
            "tuesday": False,
            "wednesday": False,
            "thursday": False,
            "friday": True,
            "saturday": False,
            "sunday": True,
            "once": False,
            "free": False,
            "not_free": False
        }
        rtn=get_next_alarm_time(alarm_time=alarmtime,start_dt=datetime(year=2022,month=5,day=15,hour=8,minute=12))
        self.assertEqual(rtn.strftime("%Y-%m-%d %H:%M"),'2022-05-15 23:42')

    def test_once(self):
        alarmtime={
            "name": "Weckzeit 3",
            "time": "06:20",
            "active": True,
            "monday": False,
            "tuesday": False,
            "wednesday": False,
            "thursday": False,
            "friday": False,
            "saturday": False,
            "sunday": False,
            "once": True,
            "free": False,
            "not_free": False
        }
        rtn=get_next_alarm_time(alarm_time=alarmtime,start_dt=datetime(year=2022,month=5,day=15,hour=8,minute=12))
        self.assertEqual(rtn.strftime("%Y-%m-%d %H:%M"),'2022-05-16 06:20')


if __name__ == '__main__':
    unittest.main()
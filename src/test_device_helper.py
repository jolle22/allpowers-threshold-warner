import unittest
from unittest.mock import Mock
from device_helper import get_minutes_till_refresh

class TestGetMinutesTillRefresh(unittest.TestCase):

    def setUp(self):
        self.allpowers_device = Mock(spec=['percent_remain', 'minutes_remain'])

    def test_battery_below_threshold(self):
        self.allpowers_device.percent_remain = 10
        self.allpowers_device.minutes_remain = 100
        result = get_minutes_till_refresh(self.allpowers_device, 20)
        self.assertEqual(result, 0)

    def test_battery_above_threshold_high_refresh_time(self):
        self.allpowers_device.percent_remain = 50
        self.allpowers_device.minutes_remain = 100
        result = get_minutes_till_refresh(self.allpowers_device, 20)
        self.assertEqual(result, 10)  # Should cap at 10 minutes

    def test_battery_above_threshold_low_refresh_time(self):
        self.allpowers_device.percent_remain = 25
        self.allpowers_device.minutes_remain = 2
        result = get_minutes_till_refresh(self.allpowers_device, 20)
        self.assertEqual(result, 1)  # Should floor at 1 minute

    def test_battery_above_threshold_medium_refresh_time(self):
        self.allpowers_device.percent_remain = 35
        self.allpowers_device.minutes_remain = 40
        result = get_minutes_till_refresh(self.allpowers_device, 20)
        self.assertEqual(result, 8.57)

    def test_battery_edge_case_equal_threshold(self):
        self.allpowers_device.percent_remain = 20
        self.allpowers_device.minutes_remain = 40
        result = get_minutes_till_refresh(self.allpowers_device, 20)
        self.assertEqual(result, 0)

if __name__ == '__main__':
    unittest.main()
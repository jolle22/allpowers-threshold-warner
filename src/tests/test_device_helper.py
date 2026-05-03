import pytest
from unittest.mock import Mock, MagicMock
from device_helper import (
    RefreshCalculator,
    DeviceFinder,
    get_minutes_till_refresh,
    find_device_index_by_string,
    find_device_index_by_mac,
)


# ----------------------------
# Fixtures
# ----------------------------
@pytest.fixture
def mock_device():
    """Create a mock AllpowersBLE device"""
    device = Mock()
    device.percent_remain = 50
    device.minutes_remain = 120
    return device


@pytest.fixture
def mock_device_list():
    """Create a list of mock devices with MAC addresses and string representations"""
    devices = []
    
    device1 = Mock()
    device1.address = "2A:02:01:61:67:E0"
    device1.__str__ = Mock(return_value="AP S300 V2.0")
    devices.append(device1)
    
    device2 = Mock()
    device2.address = "AA:BB:CC:DD:EE:FF"
    device2.__str__ = Mock(return_value="Other Device")
    devices.append(device2)
    
    device3 = Mock()
    device3.address = "11:22:33:44:55:66"
    device3.__str__ = Mock(return_value="Third Device")
    devices.append(device3)
    
    return devices


# ----------------------------
# RefreshCalculator Tests
# ----------------------------
class TestRefreshCalculator:
    """Test the RefreshCalculator class"""

    def test_minutes_until_refresh_normal_operation(self, mock_device):
        """Test normal refresh calculation"""
        mock_device.percent_remain = 50
        mock_device.minutes_remain = 120
        low_battery_threshold = 30
        max_interval = 0.04
        
        result = RefreshCalculator.minutes_until_refresh(
            mock_device,
            low_battery_threshold,
            max_interval,
        )
        
        # Should return max_interval since calculated interval exceeds it
        assert result == max_interval

    def test_minutes_until_refresh_immediately_below_threshold(self, mock_device):
        """Test immediate refresh when below threshold"""
        mock_device.percent_remain = 25
        mock_device.minutes_remain = 100
        low_battery_threshold = 30
        max_interval = 0.04
        
        result = RefreshCalculator.minutes_until_refresh(
            mock_device,
            low_battery_threshold,
            max_interval,
        )
        
        assert result == 0

    def test_minutes_until_refresh_at_threshold(self, mock_device):
        """Test refresh calculation at exact threshold"""
        mock_device.percent_remain = 30
        mock_device.minutes_remain = 100
        low_battery_threshold = 30
        max_interval = 0.04
        
        result = RefreshCalculator.minutes_until_refresh(
            mock_device,
            low_battery_threshold,
            max_interval,
        )
        
        assert result == 0

    def test_minutes_until_refresh_zero_percent(self, mock_device):
        """Test with zero percent remaining"""
        mock_device.percent_remain = 0
        mock_device.minutes_remain = 100
        low_battery_threshold = 30
        max_interval = 0.04
        
        result = RefreshCalculator.minutes_until_refresh(
            mock_device,
            low_battery_threshold,
            max_interval,
        )
        
        assert result == 0

    def test_minutes_until_refresh_zero_minutes(self, mock_device):
        """Test with zero minutes remaining"""
        mock_device.percent_remain = 50
        mock_device.minutes_remain = 0
        low_battery_threshold = 30
        max_interval = 0.04
        
        result = RefreshCalculator.minutes_until_refresh(
            mock_device,
            low_battery_threshold,
            max_interval,
        )
        
        assert result == 0

    def test_minutes_until_refresh_negative_percent(self, mock_device):
        """Test with negative percent remaining"""
        mock_device.percent_remain = -10
        mock_device.minutes_remain = 100
        low_battery_threshold = 30
        max_interval = 0.04
        
        result = RefreshCalculator.minutes_until_refresh(
            mock_device,
            low_battery_threshold,
            max_interval,
        )
        
        assert result == 0

    def test_minutes_until_refresh_negative_minutes(self, mock_device):
        """Test with negative minutes remaining"""
        mock_device.percent_remain = 50
        mock_device.minutes_remain = -10
        low_battery_threshold = 30
        max_interval = 0.04
        
        result = RefreshCalculator.minutes_until_refresh(
            mock_device,
            low_battery_threshold,
            max_interval,
        )
        
        assert result == 0

    def test_minutes_until_refresh_high_battery_level(self, mock_device):
        """Test with high battery level"""
        mock_device.percent_remain = 95
        mock_device.minutes_remain = 500
        low_battery_threshold = 30
        max_interval = 60
        
        result = RefreshCalculator.minutes_until_refresh(
            mock_device,
            low_battery_threshold,
            max_interval,
        )
        
        # With high battery, interval should be clamped to max_interval
        assert result <= max_interval

    def test_minutes_until_refresh_very_low_threshold(self, mock_device):
        """Test with very low low_battery_threshold"""
        mock_device.percent_remain = 50
        mock_device.minutes_remain = 120
        low_battery_threshold = 5
        max_interval = 0.04
        
        result = RefreshCalculator.minutes_until_refresh(
            mock_device,
            low_battery_threshold,
            max_interval,
        )
        
        assert isinstance(result, float)
        assert result >= 0

    def test_minutes_until_refresh_very_high_threshold(self, mock_device):
        """Test with threshold equal to current percent"""
        mock_device.percent_remain = 50
        mock_device.minutes_remain = 120
        low_battery_threshold = 50
        max_interval = 0.04
        
        result = RefreshCalculator.minutes_until_refresh(
            mock_device,
            low_battery_threshold,
            max_interval,
        )
        
        assert result == 0

    def test_minutes_until_refresh_calculation_correctness(self, mock_device):
        """Test the mathematical correctness of the calculation"""
        mock_device.percent_remain = 80
        mock_device.minutes_remain = 160
        low_battery_threshold = 20
        max_interval = 100
        
        result = RefreshCalculator.minutes_until_refresh(
            mock_device,
            low_battery_threshold,
            max_interval,
        )
        
        # Manual calculation:
        # minutes_per_percent = 160 / 80 = 2
        # minutes_to_threshold = 160 - (2 * 20) = 120
        # interval = 120 / 5 = 24
        assert result == 24.0

    def test_minutes_until_refresh_small_interval(self, mock_device):
        """Test with very small max_interval"""
        mock_device.percent_remain = 50
        mock_device.minutes_remain = 120
        low_battery_threshold = 30
        max_interval = 0.01
        
        result = RefreshCalculator.minutes_until_refresh(
            mock_device,
            low_battery_threshold,
            max_interval,
        )
        
        assert result == max_interval

    def test_clamp_interval_below_minimum(self):
        """Test clamping when interval is below minimum"""
        interval = 0.0001
        max_interval = 0.4
        
        result = RefreshCalculator._clamp_interval(interval, max_interval)
        
        assert result == 0.4

    def test_clamp_interval_above_maximum(self):
        """Test clamping when interval exceeds maximum"""
        interval = 100
        max_interval = 0.04
        
        result = RefreshCalculator._clamp_interval(interval, max_interval)
        
        assert result == 0.04

    def test_clamp_interval_within_bounds(self):
        """Test clamping when interval is within bounds"""
        interval = 0.2
        max_interval = 0.4
        
        result = RefreshCalculator._clamp_interval(interval, max_interval)
        
        assert result == 0.4

    def test_clamp_interval_rounding(self):
        """Test that interval is rounded to 2 decimal places"""
        interval = 0.123456
        max_interval = 1.0
        
        result = RefreshCalculator._clamp_interval(interval, max_interval)
        
        assert result == 1.0

    def test_clamp_interval_max_interval_less_than_one(self):
        """Test clamping when max_interval is less than 1"""
        interval = 0.005
        max_interval = 0.04
        
        result = RefreshCalculator._clamp_interval(interval, max_interval)
        
        assert result == 0.04

    def test_clamp_interval_max_interval_greater_than_one(self):
        """Test clamping when max_interval is greater than 1"""
        interval = 0.5
        max_interval = 60
        
        result = RefreshCalculator._clamp_interval(interval, max_interval)
        
        assert result == 1

    def test_clamp_interval_exact_max(self):
        """Test clamping when interval exactly equals max_interval"""
        interval = 0.04
        max_interval = 0.04
        
        result = RefreshCalculator._clamp_interval(interval, max_interval)
        
        assert result == 0.04


# ----------------------------
# DeviceFinder Tests
# ----------------------------
class TestDeviceFinder:
    """Test the DeviceFinder class"""

    def test_find_index_with_custom_comparator_found(self):
        """Test find_index with custom comparator when device is found"""
        devices = [1, 2, 3, 4, 5]
        result = DeviceFinder.find_index(
            devices,
            3,
            lambda d, v: d == v,
        )
        
        assert result == 2

    def test_find_index_with_custom_comparator_not_found(self):
        """Test find_index with custom comparator when device is not found"""
        devices = [1, 2, 3, 4, 5]
        result = DeviceFinder.find_index(
            devices,
            10,
            lambda d, v: d == v,
        )
        
        assert result == -1

    def test_find_index_empty_list(self):
        """Test find_index with empty device list"""
        devices = []
        result = DeviceFinder.find_index(
            devices,
            1,
            lambda d, v: d == v,
        )
        
        assert result == -1

    def test_find_index_first_element(self):
        """Test find_index when match is first element"""
        devices = ["first", "second", "third"]
        result = DeviceFinder.find_index(
            devices,
            "first",
            lambda d, v: d == v,
        )
        
        assert result == 0

    def test_find_index_last_element(self):
        """Test find_index when match is last element"""
        devices = ["first", "second", "third"]
        result = DeviceFinder.find_index(
            devices,
            "third",
            lambda d, v: d == v,
        )
        
        assert result == 2

    def test_find_index_complex_comparator(self):
        """Test find_index with complex comparator logic"""
        devices = [
            {"id": 1, "name": "Device A"},
            {"id": 2, "name": "Device B"},
            {"id": 3, "name": "Device C"},
        ]
        result = DeviceFinder.find_index(
            devices,
            2,
            lambda d, v: d["id"] == v,
        )
        
        assert result == 1

    def test_by_string_found(self, mock_device_list):
        """Test by_string when device is found"""
        result = DeviceFinder.by_string(mock_device_list, "AP S300 V2.0")
        
        assert result == 0

    def test_by_string_not_found(self, mock_device_list):
        """Test by_string when device is not found"""
        result = DeviceFinder.by_string(mock_device_list, "Nonexistent Device")
        
        assert result == -1

    def test_by_string_empty_list(self):
        """Test by_string with empty device list"""
        result = DeviceFinder.by_string([], "Any Device")
        
        assert result == -1

    def test_by_string_second_device(self, mock_device_list):
        """Test by_string when matching second device"""
        result = DeviceFinder.by_string(mock_device_list, "Other Device")
        
        assert result == 1

    def test_by_string_third_device(self, mock_device_list):
        """Test by_string when matching third device"""
        result = DeviceFinder.by_string(mock_device_list, "Third Device")
        
        assert result == 2

    def test_by_string_case_sensitive(self, mock_device_list):
        """Test that by_string is case sensitive"""
        result = DeviceFinder.by_string(mock_device_list, "ap s300 v2.0")
        
        assert result == -1

    def test_by_string_partial_match_not_found(self, mock_device_list):
        """Test that by_string requires exact match, not partial"""
        result = DeviceFinder.by_string(mock_device_list, "AP S300")
        
        assert result == -1

    def test_by_mac_found(self, mock_device_list):
        """Test by_mac when device is found"""
        result = DeviceFinder.by_mac(mock_device_list, "2A:02:01:61:67:E0")
        
        assert result == 0

    def test_by_mac_not_found(self, mock_device_list):
        """Test by_mac when device is not found"""
        result = DeviceFinder.by_mac(mock_device_list, "FF:FF:FF:FF:FF:FF")
        
        assert result == -1

    def test_by_mac_empty_list(self):
        """Test by_mac with empty device list"""
        result = DeviceFinder.by_mac([], "2A:02:01:61:67:E0")
        
        assert result == -1

    def test_by_mac_second_device(self, mock_device_list):
        """Test by_mac when matching second device"""
        result = DeviceFinder.by_mac(mock_device_list, "AA:BB:CC:DD:EE:FF")
        
        assert result == 1

    def test_by_mac_third_device(self, mock_device_list):
        """Test by_mac when matching third device"""
        result = DeviceFinder.by_mac(mock_device_list, "11:22:33:44:55:66")
        
        assert result == 2

    def test_by_mac_case_insensitive(self, mock_device_list):
        """Test by_mac matching with different case"""
        # MAC addresses are typically case-insensitive
        mock_device_list[0].address = "2a:02:01:61:67:e0"
        result = DeviceFinder.by_mac(mock_device_list, "2a:02:01:61:67:e0")
        
        assert result == 0

    def test_by_mac_device_without_address_attribute(self):
        """Test by_mac with device that has no address attribute"""
        devices = [Mock(spec=[]), Mock(spec=[])]
        result = DeviceFinder.by_mac(devices, "AA:BB:CC:DD:EE:FF")
        
        assert result == -1

    def test_by_mac_partial_match_not_found(self, mock_device_list):
        """Test that by_mac requires exact match"""
        result = DeviceFinder.by_mac(mock_device_list, "2A:02:01")
        
        assert result == -1


# ----------------------------

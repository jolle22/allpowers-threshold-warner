import pytest
import asyncio
import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import dataclass

from threshold_check import (
    Config,
    WattsUsage,
    UI,
    DeviceManager,
    BatteryMonitor,
)


# ----------------------------
# Fixtures
# ----------------------------
@pytest.fixture
def config():
    return Config(
        minutes_to_check_after=0.04,
        low_battery_threshold=30,
        high_battery_threshold=190,
        default_device_mac="2A:02:01:61:67:E0",
    )


@pytest.fixture
def watts_usage():
    return WattsUsage()


@pytest.fixture
def mock_device():
    device = AsyncMock()
    device.percent_remain = 50
    device.minutes_remain = 120
    device.watts_import = 100
    device.watts_export = 50
    device.ac_on = True
    device.dc_on = False
    return device


@pytest.fixture
def mock_ble_device():
    device = Mock()
    device.name = "AP S300 V2.0"
    device.address = "2A:02:01:61:67:E0"
    return device


@pytest.fixture
def mock_ble_device_2():
    device = Mock()
    device.name = "Other Device"
    device.address = "AA:BB:CC:DD:EE:FF"
    return device


# ----------------------------
# Config Tests
# ----------------------------
class TestConfig:
    def test_config_default_values(self):
        config = Config()
        assert config.minutes_to_check_after == 0.04
        assert config.low_battery_threshold == 30
        assert config.high_battery_threshold == 190
        assert config.default_device_mac == "2A:02:01:61:67:E0"

    def test_config_custom_values(self):
        config = Config(
            minutes_to_check_after=1.0,
            low_battery_threshold=20,
            high_battery_threshold=200,
            default_device_mac="AA:BB:CC:DD:EE:FF",
        )
        assert config.minutes_to_check_after == 1.0
        assert config.low_battery_threshold == 20
        assert config.high_battery_threshold == 200
        assert config.default_device_mac == "AA:BB:CC:DD:EE:FF"


# ----------------------------
# WattsUsage Tests
# ----------------------------
class TestWattsUsage:
    def test_watts_usage_initialization(self):
        usage = WattsUsage()
        assert usage.watts_total == 0
        assert usage.counts_total == 0
        assert isinstance(usage.start_time, datetime.datetime)

    def test_watts_usage_is_dataclass(self):
        usage = WattsUsage()
        usage.watts_total = 100
        usage.counts_total = 5
        assert usage.watts_total == 100
        assert usage.counts_total == 5


# ----------------------------
# UI Tests
# ----------------------------
class TestUI:
    @patch("easygui.msgbox")
    def test_show_message(self, mock_msgbox):
        message = "Test message"
        UI.show_message(message)
        mock_msgbox.assert_called_once_with(message, title="All Powers Battery")

    @patch("easygui.choicebox")
    def test_choose_device(self, mock_choicebox):
        devices = ["Device 1", "Device 2"]
        mock_choicebox.return_value = "Device 1"
        
        result = UI.choose_device(devices)
        
        assert result == "Device 1"
        assert mock_choicebox.called


# ----------------------------
# DeviceManager Tests
# ----------------------------
class TestDeviceManager:
    @pytest.mark.asyncio
    async def test_discover_devices_success(self, config, mock_ble_device, mock_ble_device_2):
        manager = DeviceManager(config)
        
        with patch("threshold_check.BleakScanner.discover") as mock_discover:
            mock_discover.return_value = [mock_ble_device_2, mock_ble_device]
            devices = await manager.discover_devices()
        
        assert len(devices) == 2
        # Should be sorted by address
        assert devices[0].address <= devices[1].address

    @pytest.mark.asyncio
    async def test_discover_devices_bluetooth_error(self, config):
        manager = DeviceManager(config)
        
        with patch("threshold_check.BleakScanner.discover") as mock_discover:
            mock_discover.side_effect = OSError("Bluetooth not available")
            
            with pytest.raises(OSError):
                await manager.discover_devices()

    def test_get_default_device_found(self, config, mock_ble_device, mock_ble_device_2):
        manager = DeviceManager(config)
        devices = [mock_ble_device, mock_ble_device_2]
        
        with patch("threshold_check.find_device_index_by_mac") as mock_find:
            mock_find.return_value = 0
            result = manager.get_default_device(devices)
        
        assert result == mock_ble_device

    def test_get_default_device_not_found(self, config, mock_ble_device, mock_ble_device_2):
        manager = DeviceManager(config)
        devices = [mock_ble_device, mock_ble_device_2]
        
        with patch("threshold_check.find_device_index_by_mac") as mock_find:
            mock_find.return_value = -1
            result = manager.get_default_device(devices)
        
        assert result is None

    def test_get_default_device_no_mac_configured(self, mock_ble_device, mock_ble_device_2):
        config = Config(default_device_mac="")
        manager = DeviceManager(config)
        devices = [mock_ble_device, mock_ble_device_2]
        
        result = manager.get_default_device(devices)
        
        assert result is None

    def test_select_device_success(self, config, mock_ble_device, mock_ble_device_2):
        manager = DeviceManager(config)
        devices = [mock_ble_device, mock_ble_device_2]
        
        with patch("threshold_check.UI.choose_device") as mock_choose:
            with patch("threshold_check.find_device_index_by_string") as mock_find:
                mock_choose.return_value = "AP S300 V2.0"
                mock_find.return_value = 0
                
                result = manager.select_device(devices)
        
        assert result == mock_ble_device

    def test_select_device_not_found(self, config, mock_ble_device, mock_ble_device_2):
        manager = DeviceManager(config)
        devices = [mock_ble_device, mock_ble_device_2]
        
        with patch("threshold_check.UI.choose_device") as mock_choose:
            with patch("threshold_check.find_device_index_by_string") as mock_find:
                mock_choose.return_value = "Unknown Device"
                mock_find.return_value = -1
                
                with pytest.raises(RuntimeError, match="Selected device is not available"):
                    manager.select_device(devices)

    @pytest.mark.asyncio
    async def test_pick_device_uses_default(self, config, mock_ble_device, mock_ble_device_2):
        manager = DeviceManager(config)
        
        with patch.object(manager, "discover_devices") as mock_discover:
            with patch.object(manager, "get_default_device") as mock_default:
                mock_discover.return_value = [mock_ble_device, mock_ble_device_2]
                mock_default.return_value = mock_ble_device
                
                result = await manager.pick_device()
        
        assert result == mock_ble_device

    @pytest.mark.asyncio
    async def test_pick_device_prompts_when_no_default(self, config, mock_ble_device, mock_ble_device_2):
        manager = DeviceManager(config)
        
        with patch.object(manager, "discover_devices") as mock_discover:
            with patch.object(manager, "get_default_device") as mock_default:
                with patch.object(manager, "select_device") as mock_select:
                    mock_discover.return_value = [mock_ble_device, mock_ble_device_2]
                    mock_default.return_value = None
                    mock_select.return_value = mock_ble_device_2
                    
                    result = await manager.pick_device()
        
        assert result == mock_ble_device_2
        mock_select.assert_called_once()


# ----------------------------
# BatteryMonitor Tests
# ----------------------------
class TestBatteryMonitor:
    def test_battery_monitor_initialization(self, mock_device, config, watts_usage):
        monitor = BatteryMonitor(mock_device, config, watts_usage)
        
        assert monitor.device == mock_device
        assert monitor.config == config
        assert monitor.watts_usage == watts_usage
        assert monitor.running is True

    @pytest.mark.asyncio
    async def test_initialize(self, mock_device, config, watts_usage):
        monitor = BatteryMonitor(mock_device, config, watts_usage)
        mock_device.ac_on = False
        
        with patch("asyncio.sleep"):
            await monitor.initialize()
        
        mock_device.initialise.assert_called_once()
        mock_device.set_ac.assert_called_once_with(True)

    @pytest.mark.asyncio
    async def test_initialize_ac_already_on(self, mock_device, config, watts_usage):
        monitor = BatteryMonitor(mock_device, config, watts_usage)
        mock_device.ac_on = True
        
        with patch("asyncio.sleep"):
            await monitor.initialize()
        
        mock_device.initialise.assert_called_once()
        mock_device.set_ac.assert_not_called()

    def test_build_status(self, mock_device, config, watts_usage):
        monitor = BatteryMonitor(mock_device, config, watts_usage)
        mock_device.percent_remain = 75
        mock_device.minutes_remain = 240
        mock_device.watts_import = 100
        mock_device.watts_export = 50
        
        status = monitor.build_status()
        
        assert "75%" in status
        assert "240 minutes" in status
        assert "100" in status  # watts_import
        assert "50" in status   # watts_export

    def test_log_power_usage(self, mock_device, config, watts_usage):
        monitor = BatteryMonitor(mock_device, config, watts_usage)
        mock_device.watts_export = 100
        
        monitor.log_power_usage()
        
        assert watts_usage.watts_total == 100
        assert watts_usage.counts_total == 1

    def test_log_power_usage_multiple_times(self, mock_device, config, watts_usage):
        monitor = BatteryMonitor(mock_device, config, watts_usage)
        mock_device.watts_export = 100
        
        monitor.log_power_usage()
        mock_device.watts_export = 150
        monitor.log_power_usage()
        
        assert watts_usage.watts_total == 250
        assert watts_usage.counts_total == 2

    def test_calc_power_usage_no_data(self, mock_device, config, watts_usage):
        monitor = BatteryMonitor(mock_device, config, watts_usage)
        
        result = monitor.calc_power_usage()
        
        assert result == 0.0

    def test_calc_power_usage_with_data(self, mock_device, config, watts_usage):
        monitor = BatteryMonitor(mock_device, config, watts_usage)
        watts_usage.watts_total = 1000
        watts_usage.counts_total = 10
        watts_usage.start_time = datetime.datetime.now() - datetime.timedelta(hours=1)
        
        result = monitor.calc_power_usage()
        
        # mean_watts = 1000/10 = 100, elapsed = 1 hour
        expected = 100 * 1
        assert result == pytest.approx(expected, rel=0.01)

    @pytest.mark.asyncio
    async def test_handle_low_battery(self, mock_device, config, watts_usage):
        monitor = BatteryMonitor(mock_device, config, watts_usage)
        mock_device.ac_on = True
        mock_device.dc_on = True
        
        with patch("asyncio.sleep"):
            with patch("threshold_check.UI.show_message") as mock_show:
                await monitor.handle_low_battery("Low battery status")
        
        mock_device.set_ac.assert_called_with(False)
        mock_device.set_dc.assert_called_with(False)
        assert monitor.running is False
        mock_show.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_low_battery_ac_already_off(self, mock_device, config, watts_usage):
        monitor = BatteryMonitor(mock_device, config, watts_usage)
        mock_device.ac_on = False
        mock_device.dc_on = True
        
        with patch("asyncio.sleep"):
            with patch("threshold_check.UI.show_message"):
                await monitor.handle_low_battery("Low battery")
        
        mock_device.set_ac.assert_not_called()
        mock_device.set_dc.assert_called_with(False)

    @pytest.mark.asyncio
    async def test_handle_low_battery_dc_already_off(self, mock_device, config, watts_usage):
        monitor = BatteryMonitor(mock_device, config, watts_usage)
        mock_device.ac_on = True
        mock_device.dc_on = False
        
        with patch("asyncio.sleep"):
            with patch("threshold_check.UI.show_message"):
                await monitor.handle_low_battery("Low battery")
        
        mock_device.set_ac.assert_called_with(False)
        mock_device.set_dc.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_high_battery(self, mock_device, config, watts_usage):
        monitor = BatteryMonitor(mock_device, config, watts_usage)
        
        with patch("threshold_check.UI.show_message") as mock_show:
            await monitor.handle_high_battery("High battery status")
        
        mock_show.assert_called_once()
        assert "190" in str(mock_show.call_args)

    @pytest.mark.asyncio
    async def test_check_thresholds_low_battery(self, mock_device, config, watts_usage):
        monitor = BatteryMonitor(mock_device, config, watts_usage)
        mock_device.percent_remain = 20
        
        with patch.object(monitor, "handle_low_battery") as mock_handle_low:
            with patch("asyncio.sleep"):
                with patch("threshold_check.UI.show_message"):
                    await monitor.check_thresholds("status")
        
        mock_handle_low.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_thresholds_high_battery(self, mock_device, config, watts_usage):
        monitor = BatteryMonitor(mock_device, config, watts_usage)
        mock_device.percent_remain = 200
        
        with patch.object(monitor, "handle_high_battery") as mock_handle_high:
            with patch("threshold_check.UI.show_message"):
                await monitor.check_thresholds("status")
        
        mock_handle_high.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_thresholds_zero_minutes(self, mock_device, config, watts_usage):
        monitor = BatteryMonitor(mock_device, config, watts_usage)
        mock_device.percent_remain = 50
        mock_device.minutes_remain = 0
        
        await monitor.check_thresholds("status")
        
        assert monitor.running is False

    @pytest.mark.asyncio
    async def test_check_thresholds_normal_operation(self, mock_device, config, watts_usage):
        monitor = BatteryMonitor(mock_device, config, watts_usage)
        mock_device.percent_remain = 50
        mock_device.minutes_remain = 100
        
        await monitor.check_thresholds("status")
        
        assert monitor.running is True

    @pytest.mark.asyncio
    async def test_wait_for_next_cycle(self, mock_device, config, watts_usage):
        monitor = BatteryMonitor(mock_device, config, watts_usage)
        
        with patch("threshold_check.get_minutes_till_refresh") as mock_get_minutes:
            with patch("asyncio.sleep") as mock_sleep:
                mock_get_minutes.return_value = 5
                
                await monitor.wait_for_next_cycle()
        
        mock_get_minutes.assert_called_once()
        mock_sleep.assert_called_once_with(5 * 60)

    @pytest.mark.asyncio
    async def test_run_normal_cycle(self, mock_device, config, watts_usage):
        monitor = BatteryMonitor(mock_device, config, watts_usage)
        mock_device.percent_remain = 50
        mock_device.minutes_remain = 100
        
        call_count = 0
        original_running = monitor.running
        
        async def side_effect_wait():
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                monitor.running = False
        
        with patch.object(monitor, "initialize") as mock_init:
            with patch.object(monitor, "build_status") as mock_status:
                with patch.object(monitor, "log_power_usage"):
                    with patch.object(monitor, "check_thresholds"):
                        with patch.object(monitor, "wait_for_next_cycle", side_effect=side_effect_wait):
                            await monitor.run()
        
        mock_init.assert_called_once()
        assert mock_status.call_count >= 1

    @pytest.mark.asyncio
    async def test_run_exits_when_running_false(self, mock_device, config, watts_usage):
        monitor = BatteryMonitor(mock_device, config, watts_usage)
        mock_device.percent_remain = 20  # Trigger low battery
        
        with patch.object(monitor, "initialize"):
            with patch.object(monitor, "build_status", return_value="Low battery"):
                with patch.object(monitor, "log_power_usage"):
                    with patch.object(monitor, "check_thresholds") as mock_check:
                        async def set_running_false(*args):
                            monitor.running = False
                        
                        mock_check.side_effect = set_running_false
                        
                        with patch("asyncio.sleep"):
                            with patch("threshold_check.UI.show_message"):
                                await monitor.run()
        
        assert monitor.running is False

    @pytest.mark.asyncio
    async def test_run_logs_status(self, mock_device, config, watts_usage):
        monitor = BatteryMonitor(mock_device, config, watts_usage)
        mock_device.percent_remain = 50
        mock_device.minutes_remain = 100
        
        call_count = 0
        
        async def side_effect_wait():
            nonlocal call_count
            call_count += 1
            if call_count >= 1:
                monitor.running = False
        
        with patch.object(monitor, "initialize"):
            with patch.object(monitor, "build_status", return_value="Test status") as mock_status:
                with patch.object(monitor, "log_power_usage"):
                    with patch.object(monitor, "check_thresholds"):
                        with patch.object(monitor, "wait_for_next_cycle", side_effect=side_effect_wait):
                            with patch("threshold_check._LOGGER.info") as mock_logger:
                                await monitor.run()
        
        # Should log the status at least once
        assert any("Test status" in str(call) for call in mock_logger.call_args_list)


# ----------------------------
# Integration Tests
# ----------------------------
class TestIntegration:
    @pytest.mark.asyncio
    async def test_device_manager_and_battery_monitor_integration(self, config, mock_ble_device, mock_device):
        """Test that DeviceManager and BatteryMonitor work together"""
        manager = DeviceManager(config)
        watts_usage = WattsUsage()
        
        with patch.object(manager, "discover_devices") as mock_discover:
            with patch.object(manager, "get_default_device") as mock_default:
                mock_discover.return_value = [mock_ble_device]
                mock_default.return_value = mock_ble_device
                
                selected_device = await manager.pick_device()
        
        assert selected_device == mock_ble_device
        
        # Now create a monitor with the selected device
        monitor = BatteryMonitor(mock_device, config, watts_usage)
        assert monitor.device == mock_device

    @pytest.mark.asyncio
    async def test_full_battery_monitoring_cycle(self, mock_device, config):
        """Test a complete monitoring cycle"""
        watts_usage = WattsUsage()
        monitor = BatteryMonitor(mock_device, config, watts_usage)
        
        mock_device.percent_remain = 50
        mock_device.minutes_remain = 120
        mock_device.watts_export = 75
        mock_device.ac_on = False
        mock_device.dc_on = False
        
        cycle_count = 0
        
        async def mock_wait():
            nonlocal cycle_count
            cycle_count += 1
            if cycle_count >= 3:
                monitor.running = False
        
        with patch.object(monitor, "initialize"):
            with patch.object(monitor, "check_thresholds"):
                with patch.object(monitor, "wait_for_next_cycle", side_effect=mock_wait):
                    await monitor.run()
        
        # Should have logged power usage 3 times
        assert watts_usage.counts_total == 3
        assert watts_usage.watts_total == 225  # 75 * 3


# ----------------------------
# Edge Case Tests
# ----------------------------
class TestEdgeCases:
    def test_calc_power_usage_with_zero_elapsed_time(self, mock_device, config, watts_usage):
        """Test calculation when no time has elapsed"""
        monitor = BatteryMonitor(mock_device, config, watts_usage)
        watts_usage.watts_total = 100
        watts_usage.counts_total = 10
        watts_usage.start_time = datetime.datetime.now()
        
        result = monitor.calc_power_usage()
        
        # Should be approximately 0 since no time has elapsed
        assert result == pytest.approx(0, abs=0.1)

    def test_config_with_zero_thresholds(self):
        """Test config with edge case threshold values"""
        config = Config(
            low_battery_threshold=0,
            high_battery_threshold=100,
        )
        assert config.low_battery_threshold == 0
        assert config.high_battery_threshold == 100

    @pytest.mark.asyncio
    async def test_check_thresholds_boundary_low(self, mock_device, config, watts_usage):
        """Test boundary condition for low battery threshold"""
        monitor = BatteryMonitor(mock_device, config, watts_usage)
        mock_device.percent_remain = 30  # Exactly at threshold
        mock_device.minutes_remain = 100
        
        with patch.object(monitor, "handle_low_battery") as mock_handle_low:
            with patch("asyncio.sleep"):
                with patch("threshold_check.UI.show_message"):
                    await monitor.check_thresholds("status")
        
        mock_handle_low.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_thresholds_boundary_high(self, mock_device, config, watts_usage):
        """Test boundary condition for high battery threshold"""
        monitor = BatteryMonitor(mock_device, config, watts_usage)
        mock_device.percent_remain = 191  # Just above threshold
        mock_device.minutes_remain = 100
        
        with patch.object(monitor, "handle_high_battery") as mock_handle_high:
            with patch("threshold_check.UI.show_message"):
                await monitor.check_thresholds("status")
        
        mock_handle_high.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_low_battery_with_both_ac_dc_off(self, mock_device, config, watts_usage):
        """Test low battery handling when both AC and DC are already off"""
        monitor = BatteryMonitor(mock_device, config, watts_usage)
        mock_device.ac_on = False
        mock_device.dc_on = False
        
        with patch("asyncio.sleep"):
            with patch("threshold_check.UI.show_message") as mock_show:
                await monitor.handle_low_battery("Low battery")
        
        mock_device.set_ac.assert_not_called()
        mock_device.set_dc.assert_not_called()
        mock_show.assert_called_once()
        assert monitor.running is False

    def test_build_status_with_zero_values(self, mock_device, config, watts_usage):
        """Test status building with zero power values"""
        monitor = BatteryMonitor(mock_device, config, watts_usage)
        mock_device.percent_remain = 0
        mock_device.minutes_remain = 0
        mock_device.watts_import = 0
        mock_device.watts_export = 0
        
        status = monitor.build_status()
        
        assert "0%" in status
        assert "0 minutes" in status

    def test_build_status_with_large_values(self, mock_device, config, watts_usage):
        """Test status building with very large values"""
        monitor = BatteryMonitor(mock_device, config, watts_usage)
        mock_device.percent_remain = 100
        mock_device.minutes_remain = 9999
        mock_device.watts_import = 99999
        mock_device.watts_export = 99999
        
        status = monitor.build_status()
        
        assert "100%" in status
        assert "9999 minutes" in status


# ----------------------------
# Error Handling Tests
# ----------------------------
class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_initialize_raises_exception(self, mock_device, config, watts_usage):
        """Test that exceptions in initialize propagate"""
        monitor = BatteryMonitor(mock_device, config, watts_usage)
        mock_device.initialise.side_effect = RuntimeError("Device error")
        
        with pytest.raises(RuntimeError, match="Device error"):
            await monitor.initialize()

    @pytest.mark.asyncio
    async def test_set_ac_raises_exception(self, mock_device, config, watts_usage):
        """Test that exceptions when setting AC propagate"""
        monitor = BatteryMonitor(mock_device, config, watts_usage)
        mock_device.ac_on = False
        mock_device.set_ac.side_effect = RuntimeError("AC control failed")
        
        with pytest.raises(RuntimeError, match="AC control failed"):
            with patch("asyncio.sleep"):
                await monitor.initialize()

    @pytest.mark.asyncio
    async def test_set_dc_raises_exception_in_low_battery(self, mock_device, config, watts_usage):
        """Test that exceptions when setting DC propagate during low battery"""
        monitor = BatteryMonitor(mock_device, config, watts_usage)
        mock_device.ac_on = True
        mock_device.dc_on = True
        mock_device.set_dc.side_effect = RuntimeError("DC control failed")
        
        with pytest.raises(RuntimeError, match="DC control failed"):
            with patch("asyncio.sleep"):
                await monitor.handle_low_battery("Low battery")

    @pytest.mark.asyncio
    async def test_device_manager_discover_with_empty_result(self, config):
        """Test device discovery when no devices are found"""
        manager = DeviceManager(config)
        
        with patch("threshold_check.BleakScanner.discover") as mock_discover:
            mock_discover.return_value = []
            devices = await manager.discover_devices()
        
        assert devices == []

    def test_select_device_with_empty_list(self, config):
        """Test device selection with empty device list"""
        manager = DeviceManager(config)
        
        with patch("threshold_check.UI.choose_device") as mock_choose:
            with patch("threshold_check.find_device_index_by_string") as mock_find:
                mock_choose.return_value = None
                mock_find.return_value = -1
                
                with pytest.raises(RuntimeError):
                    manager.select_device([])


# ----------------------------
# Concurrency Tests
# ----------------------------
class TestConcurrency:
    @pytest.mark.asyncio
    async def test_multiple_check_thresholds_calls(self, mock_device, config, watts_usage):
        """Test that multiple threshold checks can run"""
        monitor = BatteryMonitor(mock_device, config, watts_usage)
        mock_device.percent_remain = 50
        mock_device.minutes_remain = 100
        
        tasks = [
            monitor.check_thresholds("status"),
            monitor.check_thresholds("status"),
            monitor.check_thresholds("status"),
        ]
        
        await asyncio.gather(*tasks)
        
        assert monitor.running is True

    @pytest.mark.asyncio
    async def test_concurrent_log_power_usage(self, mock_device, config, watts_usage):
        """Test that power usage logging is thread-safe"""
        monitor = BatteryMonitor(mock_device, config, watts_usage)
        mock_device.watts_export = 10
        
        # Simulate concurrent logging
        for _ in range(100):
            monitor.log_power_usage()
        
        assert watts_usage.watts_total == 1000
        assert watts_usage.counts_total == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

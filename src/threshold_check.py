import asyncio
import logging
import datetime
from dataclasses import dataclass

import easygui
from bleak import BleakScanner

from allpowers_ble import AllpowersBLE
from device_helper import (
    get_minutes_till_refresh,
    find_device_index_by_string,
    find_device_index_by_mac,
)

_LOGGER = logging.getLogger(__name__)

WINDOW_TITLE = "All Powers Battery"

@dataclass
class WattsUsage:
    watts_total = 0
    counts_total = 0
    start_time = datetime.datetime.now()

# ----------------------------
# Configuration
# ----------------------------
@dataclass
class Config:
    minutes_to_check_after: float = 0.04
    low_battery_threshold: int = 30
    high_battery_threshold: int = 190
    default_device_mac: str = "2A:02:01:61:67:E0"


# ----------------------------
# UI Helpers
# ----------------------------
class UI:
    @staticmethod
    def show_message(message: str):
        easygui.msgbox(message, title=WINDOW_TITLE)

    @staticmethod
    def choose_device(devices):
        text = (
            "Select the All Powers bluetooth device.\n"
            "Their address usually starts with '2A:'."
            "Their name can be similar to 'AP S300 V2.0' or 'None'"
        )
        return easygui.choicebox(text, WINDOW_TITLE, devices)


# ----------------------------
# Device Manager
# ----------------------------
class DeviceManager:
    def __init__(self, config: Config):
        self.config = config

    async def discover_devices(self):
        try:
            devices = await BleakScanner.discover()
        except OSError as error:
            _LOGGER.error(
                "Bluetooth must be enabled on this device and the power station."
            )
            raise error

        return sorted(devices, key=lambda x: x.address)

    def get_default_device(self, devices):
        if self.config.default_device_mac:
            index = find_device_index_by_mac(
                devices, self.config.default_device_mac
            )
            if index > -1:
                return devices[index]
        return None

    def select_device(self, devices):
        selected = UI.choose_device(devices)
        index = find_device_index_by_string(devices, selected)

        if index == -1:
            raise RuntimeError("Selected device is not available")

        return devices[index]

    async def pick_device(self):
        devices = await self.discover_devices()

        default = self.get_default_device(devices)
        if default:
            return default

        return self.select_device(devices)


# ----------------------------
# Battery Monitor
# ----------------------------
class BatteryMonitor:
    def __init__(self, device: AllpowersBLE, config: Config, watts_usage: WattsUsage):
        self.device = device
        self.config = config
        self.watts_usage = watts_usage
        self.running = True

    async def initialize(self):
        await self.device.initialise()
        await asyncio.sleep(2)

        if not self.device.ac_on:
            await self.device.set_ac(True)

    def build_status(self) -> str:
        return (
            f"{self.device.percent_remain}% charged and "
            f"{self.device.minutes_remain} minutes remain. "
            f"Power input: {self.device.watts_import}. "
            f"Power output: {self.device.watts_export}"
        )
    
    def log_power_usage(self) -> str:
        self.watts_usage.watts_total += self.device.watts_export
        self.watts_usage.counts_total += 1
        
    def calc_power_usage(self) -> str:        
        mean_watts = (
            self.watts_usage.watts_total / self.watts_usage.counts_total
            if self.watts_usage.counts_total
            else 0.0
        )
        elapsed = (datetime.datetime.now() - self.watts_usage.start_time).total_seconds() / 3600.0
        return mean_watts * elapsed
        

    async def handle_low_battery(self, status: str):

        if self.device.ac_on:
            await self.device.set_ac(False)
            if self.device.dc_on:
                await asyncio.sleep(2)

        if self.device.dc_on:
            await self.device.set_dc(False)

        self.running = False
        
        UI.show_message(
            f"{status}\nPower was shut off. Please charge the battery.\n"
            f"About {self.calc_power_usage()} Watt Hours where used."
        )

    async def handle_high_battery(self, status: str):
        UI.show_message(
            f"The charge is above {self.config.high_battery_threshold}%.\n{status}"
        )

    async def check_thresholds(self, status: str):
        if self.device.percent_remain <= self.config.low_battery_threshold:
            await self.handle_low_battery(status)

        elif self.device.percent_remain > self.config.high_battery_threshold:
            await self.handle_high_battery(status)

        if self.device.minutes_remain == 0:
            self.running = False

    async def wait_for_next_cycle(self):
        minutes = get_minutes_till_refresh(
            self.device,
            self.config.low_battery_threshold,
            self.config.minutes_to_check_after,
        )

        _LOGGER.info(
            "Next refresh in %s",
            datetime.timedelta(seconds=minutes * 60),
        )

        await asyncio.sleep(minutes * 60)

    async def run(self):
        await self.initialize()

        while self.running:
            status = self.build_status()
            _LOGGER.info(status)
            self.log_power_usage()

            await self.check_thresholds(status)

            if self.running:
                await self.wait_for_next_cycle()


# ----------------------------
# Application Entry Point
# ----------------------------
async def main():
    watts_usage = WattsUsage()
    config = Config()

    manager = DeviceManager(config)
    selected_device = await manager.pick_device()

    device = AllpowersBLE(selected_device)
    monitor = BatteryMonitor(device, config, watts_usage)

    await monitor.run()



# ----------------------------
# Bootstrap
# ----------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logging.getLogger("allpowersdevice").setLevel(logging.DEBUG)

    asyncio.run(main())
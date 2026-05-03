from typing import Callable, Iterable, Any, Optional
from allpowers_ble import AllpowersBLE


# ----------------------------
# Refresh Calculation
# ----------------------------
class RefreshCalculator:
    @staticmethod
    def minutes_until_refresh(
        device: AllpowersBLE,
        low_battery_threshold: int,
        max_interval_minutes: float,
    ) -> float:
        """
        Calculate how long to wait before the next refresh.

        Rules:
        - Immediate refresh if below threshold
        - Dynamically calculate based on discharge rate
        - Clamp between sensible bounds
        """

        percent = device.percent_remain
        minutes_remaining = device.minutes_remain

        # Guard against invalid values
        if percent <= 0 or minutes_remaining <= 0:
            return 0

        if percent <= low_battery_threshold:
            return 0

        minutes_per_percent = minutes_remaining / percent
        minutes_to_threshold = minutes_remaining - (
            minutes_per_percent * low_battery_threshold
        )

        # Check 5 times before hitting threshold
        interval = minutes_to_threshold / 5

        return RefreshCalculator._clamp_interval(interval, max_interval_minutes)

    @staticmethod
    def _clamp_interval(interval: float, max_interval: float) -> float:
        min_interval = min(1, max_interval)

        if interval > max_interval:
            return max_interval

        if interval < min_interval:
            return min_interval

        return round(interval, 2)


# ----------------------------
# Device Lookup Utilities
# ----------------------------
class DeviceFinder:
    @staticmethod
    def find_index(
        devices: Iterable[Any],
        value: Any,
        comparator: Callable[[Any, Any], bool],
    ) -> int:
        """
        Generic finder with custom comparison logic.
        Returns -1 if not found.
        """
        for index, device in enumerate(devices):
            if comparator(device, value):
                return index
        return -1

    @staticmethod
    def by_string(devices: Iterable[Any], output: str) -> int:
        return DeviceFinder.find_index(
            devices,
            output,
            lambda d, s: str(d) == s,
        )

    @staticmethod
    def by_mac(devices: Iterable[Any], address: str) -> int:
        return DeviceFinder.find_index(
            devices,
            address,
            lambda d, s: getattr(d, "address", None) == s,
        )


# ----------------------------
# Backward-Compatible Functions
# ----------------------------
def get_minutes_till_refresh(
    device: AllpowersBLE,
    low_battery_threshold: int,
    minutes_to_check_after: float,
) -> float:
    return RefreshCalculator.minutes_until_refresh(
        device,
        low_battery_threshold,
        minutes_to_check_after,
    )


def find_device_index_by_string(devices, output):
    return DeviceFinder.by_string(devices, output)


def find_device_index_by_mac(devices, address):
    return DeviceFinder.by_mac(devices, address)

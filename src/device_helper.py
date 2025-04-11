from allpowers_ble import AllpowersBLE

def get_minutes_till_refresh(allpowers_device: AllpowersBLE, low_battery_threshold: int, minutes_to_check_after: float):
    if allpowers_device.percent_remain <= low_battery_threshold:
        return 0

    minutes_per_percent = allpowers_device.minutes_remain / allpowers_device.percent_remain
    minutes_of_min_threshold = minutes_per_percent * low_battery_threshold
    minutes_till_min_threshold = allpowers_device.minutes_remain - minutes_of_min_threshold
    minutes_till_refresh = minutes_till_min_threshold / 3

    if minutes_till_refresh > minutes_to_check_after:
        # wait at most 10 minutes before checking again
        minutes_till_refresh = minutes_to_check_after
    elif minutes_till_refresh < min(1, minutes_to_check_after):
        # wait at least 1 minute before checking again
        minutes_till_refresh = min(1, minutes_to_check_after)
    else:
        minutes_till_refresh = round(minutes_till_refresh, 2)

    return minutes_till_refresh

def find_device_index_by_lambda(devices, device_id, compare_fn):
    index = -1
    for d in devices:
        if compare_fn(d, device_id):
            index = devices.index(d)
    return index

def find_device_index_by_string(devices, output):
    return find_device_index_by_lambda(devices, output, lambda d, s: str(d) == s)

def find_device_index_by_mac(devices, address):
    return find_device_index_by_lambda(devices, address, lambda d, s: d.address == s)

import playsound
import easygui

from allpowers_ble import AllpowersBLE

WINDOW_TITLE = "All Powers Battery"
SOUND_PATH = "resources/info.mp3"

def get_minutes_till_refresh(allpowers_device: AllpowersBLE, low_battery_threshold: int):
    if allpowers_device.percent_remain <= low_battery_threshold:
        return 0
    
    minutes_per_percent = allpowers_device.minutes_remain / allpowers_device.percent_remain 
    minutes_of_min_threshold = minutes_per_percent * low_battery_threshold
    minutes_till_min_threshold = allpowers_device.minutes_remain - minutes_of_min_threshold
    minutes_till_refresh = minutes_till_min_threshold / 2

    if minutes_till_refresh > 10:
        # wait at most 10 minutes before checking again
        minutes_till_refresh = 10
    elif minutes_till_refresh < 1:
        # wait at least 1 minutes before checking again
        minutes_till_refresh = 1
    else:
        minutes_till_refresh = round(minutes_till_refresh, 2)

    return minutes_till_refresh



async def display_message_with_sound(message: str, is_sound_active: bool):
    # the try catch is a workaround for the 1.3.0 version of playsound
    if is_sound_active:
        try:
            playsound(SOUND_PATH)
        except:
            playsound(SOUND_PATH)
    easygui.msgbox(message, title=WINDOW_TITLE)
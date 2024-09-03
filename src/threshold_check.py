import asyncio
import logging
import easygui
import datetime

from allpowers_ble import AllpowersBLE
from device_helper import get_minutes_till_refresh
from bleak import BleakScanner
from playsound import playsound

_LOGGER = logging.getLogger(__name__)

WINDOW_TITLE = "All Powers Battery"
SOUND_PATH = "resources/info.mp3"

# Configurable attributes
LOW_BATTERY_THRESHOLD = 30
HIGH_BATTERY_THRESHOLD = 90
IS_SOUND_ACTIVE = True


async def pick_device():
    text = ("Select the All Powers bluetooth device.\n"
            "Their address usually starts with '2A:'."
            "Their name can be similar to 'AP S300 V2.0' or 'None'")
    try:
        devices = await BleakScanner.discover()
    except OSError as error:
        _LOGGER.error("Make sure Bluetooth is turned on. On this device and on the power station.")
        raise error 


    devices.sort(key=lambda x: x.address, reverse=False)
    output = easygui.choicebox(text, WINDOW_TITLE, devices)

    index = -1
    for d in devices:
        if output == str(d):
            index = devices.index(d)

    if index == -1:
        _LOGGER.error("The selected device is not available")
        exit()

    return devices[index]


async def init_allpowers_ble(selected_device):
    allpowers_device: AllpowersBLE = AllpowersBLE(selected_device)
    await allpowers_device.initialise()
    await asyncio.sleep(2)

    return allpowers_device

async def run() -> None:
    selected_device = await pick_device()
    allpowers_device: AllpowersBLE = await init_allpowers_ble(selected_device)

    await allpowers_device.set_ac(True)

    run_loop = True

    while run_loop:
        status = str(allpowers_device.percent_remain) + "% charged and " + str(
            allpowers_device.minutes_remain) + " minutes remain. Power input: " + str(
            allpowers_device.watts_import) + ". Power output: " + str(allpowers_device.watts_export)

        _LOGGER.info(status)

        if allpowers_device.percent_remain <= LOW_BATTERY_THRESHOLD:
            run_loop = False
            display_message_with_sound(status + "\nPower will be shut off. Please charge the AllPowers Battery.")
            if allpowers_device.ac_on:
                await allpowers_device.set_ac(False)
                if allpowers_device.dc_on:
                    await asyncio.sleep(2)

            if allpowers_device.dc_on:
                await allpowers_device.set_dc(False)
        
        if allpowers_device.percent_remain > HIGH_BATTERY_THRESHOLD:
            await display_message_with_sound(
                "The charge is above " + str(HIGH_BATTERY_THRESHOLD) + "%.\n" + status)

        if allpowers_device.minutes_remain == 0:
            run_loop = False
            
        minutes_till_refresh = get_minutes_till_refresh(allpowers_device, LOW_BATTERY_THRESHOLD)

        _LOGGER.info("minutes till refresh: " + str(datetime.timedelta(seconds=minutes_till_refresh * 60)))
        await asyncio.sleep(minutes_till_refresh * 60)


async def display_message_with_sound(message: str):
    # the try catch is a workaround for the 1.3.0 version of playsound
    if IS_SOUND_ACTIVE:
        try:
            playsound(SOUND_PATH)
        except:
            playsound(SOUND_PATH)

    easygui.msgbox(message, title=WINDOW_TITLE)


logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logging.getLogger("allpowersdevice").setLevel(logging.DEBUG)
asyncio.run(run())

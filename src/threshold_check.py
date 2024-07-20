import logging
import easygui
import sys
from signal import Signals

from qasync import QEventLoop, QApplication, asyncSlot, asyncio
from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import QApplication, QDialog, QListWidget, QListWidgetItem
from PyQt5.uic import loadUi
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



async def get_devices():
    devices = await BleakScanner.discover()
    devices.sort(key=lambda x: x.address, reverse=False)
    return devices

async def pick_device():

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

        if allpowers_device.percent_remain < LOW_BATTERY_THRESHOLD:
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

        _LOGGER.info("minutes till refresh: " + str(minutes_till_refresh))
        await asyncio.sleep(minutes_till_refresh * 60)


async def display_message_with_sound(message: str):
    # the try catch is a workaround for the 1.3.0 version of playsound
    if IS_SOUND_ACTIVE:
        try:
            playsound(SOUND_PATH)
        except:
            playsound(SOUND_PATH)

    easygui.msgbox(message, title=WINDOW_TITLE)

class QTextBrowserLogger(logging.Handler):
    def __init__(self, logBrowser):
        super().__init__()
        self.logBrowser = logBrowser

    def emit(self, record):
        msg = self.format(record)
        self.logBrowser.append(msg)

class MainUi(QDialog):

    update_devices_signal = pyqtSignal(list)
    log_handler = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        
        self.log_handler = QTextBrowserLogger(self.logBrowser)
        
        logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S', handlers=[self.log_handler])
        logging.getLogger("allpowersdevice").setLevel(logging.DEBUG)
        self.logger = logging.getLogger(__name__)
        
        loadUi("aptw.ui", self)
        
        self.log_handler = QTextBrowserLogger(self.logBrowser)
        
        self.refreshButton.clicked.connect(self.refresh_ble_list)
        self.update_devices_signal.connect(self.update_ui)
        
        asyncio.get_event_loop().run_in_executor(None, self.refresh_ble_list)

    def update_ui(self, devices):
        self.deviceList.clear()
        self.deviceList.addItems([str(device.address +" "+str(device.name)) for device in devices])

    @asyncSlot()
    async def refresh_ble_list(self):
        devices = await get_devices()
        self.update_devices_signal.emit(devices)

if __name__ == '__main__':
    app = QApplication(sys.argv)

    event_loop = QEventLoop(app)
    asyncio.set_event_loop(event_loop)
    
    app_close_event = asyncio.Event()
    app.aboutToQuit.connect(app_close_event.set)
    
    ui = MainUi()
    ui.show()
    

    with event_loop:
        print(event_loop.is_running())
        
        event_loop.run_until_complete(app_close_event.wait())
        
    
    sys.exit(app.exec_())
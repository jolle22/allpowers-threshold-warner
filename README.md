# AllPowers threshold warner
This program uses [allpowers-ble](https://github.com/madninjaskillz/allpowers-ble) to connect to an allpowers power station.
It will give you a warning and turn of the ac/dc power supply of the allpowers battery, when the level of the battery reaches a configured threshold.
This can be used to prevent deep discharge of the battery.

## Installation
1. install dependencies

    ```pip install -r requirements.txt```
    if this fails run ```pip install wheel``` and retry

2. run __main__.py
    ```python src/threshold_check.py```
import asyncio
import threading
from src.mqttc import MQTT
from src.conn import *
import time as tm
import configparser
import sys
from src.local_message import LocalMessage
from src.logger import Logger
import os
from src.conn import *


if __name__ == '__main__':
    while check_connection() == False:
        Logger.warning("Waiting Connection")
        tm.sleep(1)

    Logger.info("Connection OK")

    config = configparser.ConfigParser()
    config_file = 'vas.config'
    config.read(config_file)

    _dev_id = config.get('Device', 'device_id')
    print("MQTT RUNNING CONFIG")
    mq = MQTT(device_id=_dev_id,
            host=config.get('Cloud', 'host'),
            port=int(config.getint('Cloud', 'port')),
            username=config.get('User', 'username'),
            password=config.get('User', 'password'),
            master_password=config.get('Device', 'master_password'))
    print("START LOOPING")
    print(f"Host {config.get('Cloud', 'host')}")
    print(f"Port {config.get('Cloud', 'port')}")
    print(f"Username {config.get('User', 'username')}")
    print(f"Password {config.get('User', 'password')}")
    print(f"Device {config.get('Device', 'master_password')}")
    
    mq.start_loop()
    mq.wait_for_connection()
    mq.subscribe(f"{_dev_id}/unicast")
    mq.subscribe(f"{_dev_id}/broadcast")
    mq.subscribe("unregister")
    mq.subscribe("register")
    mq.subscribe("who")
    mq.publish(topic=f'{_dev_id}/response', payload='Device is ON')

    # mq.init_prev_client()

    lm = LocalMessage()

    print("Start loop")
    Logger.info("Voice Alarm Device is ON")

    # Buat thread sekali saja di luar loop
    t1 = threading.Thread(target=mq.main_run)
    t1.daemon = True
    t2 = threading.Thread(target=lm.main_run)
    t2.daemon = True

    t1.start()
    t2.start()

    start_time = time.time()
    _is_ok = True

    while _is_ok:
        if mq.is_connected() == False:  
            Logger.warning("Not connected")
            os.system("sudo systemctl restart mqtt.service")

        elif mq.is_connect == False:
            Logger.warning("Not connected 2")
            os.system("sudo systemctl restart mqtt.service")
            
        elif time.time() - start_time > 60:
            mq.publish_temperature()
            start_time = time.time()

        tm.sleep(1)  # jangan lupa sleep biar gak 100% CPU
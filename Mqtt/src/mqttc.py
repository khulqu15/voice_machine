import paho.mqtt.client as mqtt
from .sys_util import *
import time
from time import sleep
import datetime
import os
from .client import Client
from .sys_util import StatusControl
import asyncio
import sys
import queue
from gtts import gTTS
from playsound import playsound
import os
import ssl
import os
from gtts import gTTS
import pygame


import re
from src.logger import Logger

class MQTT:
    def __init__(self, device_id: str, host: str, port: int, username: str, password: str, master_password: str):        
        self.device_id = device_id
        self.port = port
        self.host = host
        self.username = username
        self.password = password
        self.master_password = master_password

        self.is_connect = False
        self.list_subscribe = []
        self.task_limit = 20
        self.list_task = []

        # Set up MQTT
        self.mqtt_client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            protocol=mqtt.MQTTv5
        )
        
        self.mqtt_client.username_pw_set(self.username, self.password)

        self.mqtt_client.tls_set(
            tls_version=ssl.PROTOCOL_TLS_CLIENT
        )

        self.mqtt_client.connect_async(
            host=self.host,
            port=8883,
            keepalive=60
        )
        #self.mqtt_client.tls_set(tls_version=mqtt.ssl.PROTOCOL_TLS)
        self.mqtt_client.username_pw_set(username=self.username, password=self.password)
        self.mqtt_client.on_connect = self.__on_connect
        self.mqtt_client.on_message = self.__on_message
        self.mqtt_client.on_subscribe = self.__on_subscribe
        self.mqtt_client.on_disconnect = self.__on_disconnected
        self.mqtt_client.on_socket_close = self.__on_socket_close
        
        # Setup check queue
        self.message_queue = queue.Queue(maxsize=20)

        # Setup retry mqtt connect
        self.mqttConnect = False
        

        for attempt in range(0, 5):
            try:
                # Connect to the MQTT broker
                Logger.info(f"Attempt {attempt} to connect...")
                self.mqtt_client.connect(host=self.host, port=self.port, keepalive=60)
                self.mqttConnect = True
                break
            except Exception as e:
                Logger.error(f"Connection attempt {attempt} failed: {e}")
                self.mqttConnect = False
                time.sleep(10)
                continue
        
        if not self.mqttConnect:
            print(f"Restart Service")
            # os.system(f"sudo systemctl restart mqtt.service")
            sys.exit(1)

        # Set up client
        self.clients = Client()


    # Subscribe to all topics
    def __init_prev_client(self):
        for client in self.clients.get_clients():
            self.add_new_client(client)

    # Wait for internet conenction
    def wait_for_connection(self, timeout=15):
        start = time.time()
        while not self.is_connect:
            if time.time() - start > timeout:
                print("Timeout")
                raise TimeoutError("MQTT connection timeout")
            sleep(0.5)

    def main_run(self):
        asyncio.run(self.__async_task())

    def __on_disconnected(self, client, userdata, *args):
        Logger.warning("MQTT Disconnected")
        self.is_connect = False

    def __on_socket_close(self, client, userdata, sock):
        Logger.critical("Socket closed. Please check the network connection.")
        self.is_connect = False
    
    # Check the connection status
    def is_connected(self) -> bool:
        return self.mqtt_client.is_connected()
    
    # Subscribe to the specified topic
    def subscribe(self, topic:str):
        if self.is_connect:
            self.mqtt_client.subscribe(topic, qos=2)
    
    # Start the MQTT loop
    def start_loop(self):
        self.mqtt_client.loop_start()

    # Stop the MQTT loop
    def stop_loop(self):
        self.mqtt_client.loop_stop()

    # Callback function when the MQTT connection is established 
    def __on_connect(self, client, userdata, flags, reason_code, properties):
        Logger.info(f"MQTT Connected (v5) reason_code={reason_code}")
        print(f"MQTT Connected (v5) reason_code={reason_code}")
        if reason_code == 'Success':
            self.is_connect = True
        else:
            Logger.error(f"MQTT connection failed: {reason_code}")

    # Callback function when a message is received
    def __on_message(self, client, userdata, msg):

        _s_msg = str(msg.payload.decode('utf-8'))
        Logger.info(f'{msg.topic} -> {_s_msg}')
        print(f"msg.topic {msg.topic}")
        print(f"msg {_s_msg}")
        # Reject the message if it is retained
        if msg.retain:
            return
        
        # Get last message  
        self.last_msg = _s_msg
        
        # Register new Client
        if msg.topic == 'register':
            Logger.info(f"Register : {self.last_msg}")
            parts = self.last_msg.split("/")
            if len(parts) != 2:
                Logger.warning("Register format invalid. Use username/master_password")
                return
            username, password = parts
            if password != self.master_password:
                Logger.warning("Register rejected: wrong master password")
                return
            if not username:
                Logger.warning("Register rejected: empty username")
                return
            self.add_new_client(username)
            return
        
        # Unregister Client
        elif msg.topic == 'unregister':
            parts = self.last_msg.split("/")
            if len(parts) != 2:
                Logger.warning("Unregister format invalid")
                return
            username, password = parts
            if password != self.master_password:
                Logger.warning("Unregister rejected: wrong master password")
                return
            self.remove_client(username)
            return


        # Get device local and global IP
        elif msg.topic == 'who':
            _dev_info = f'device_id:{self.device_id}, host:{get_host()},network:['
            _all_ip = get_ip_addresses()
            _is_first = True
            for _i in _all_ip:
                if _is_first:
                    _dev_info += str(_i['ip'][0])
                    _is_first = False
                    continue
                _dev_info += ',' + str(_i['ip'][0])
            _dev_info += ']'
            self.mqtt_client.publish(topic='device', payload=_dev_info, qos=2, retain=False)
            return
        
        topic_parts = msg.topic.split("/")
        if len(topic_parts) < 2:
            return

        sender = topic_parts[0]
        msg_type = topic_parts[1]

        payload_parts = self.last_msg.split("/")
        if len(payload_parts) < 2:
            return

        target_device = payload_parts[0].strip().lower()
        command = "/".join(payload_parts[1:]).strip().lower()

        if msg_type != "unicast":
            return

        if target_device != self.device_id.lower():
            Logger.debug(f"Command ignored: target={target_device}")
            return

        Logger.info(f"UNICAST CMD → {command}")

        if command == "status":
            StatusControl.statusMessage[0] = 1

        elif command == "lamp/on":
            StatusControl.add_message_to_queue_mqtt("on")

        elif command == "lamp/off":
            StatusControl.add_message_to_queue_mqtt("off")

        elif command == "reboot":
            Logger.warning("Reboot System Request")
            self.mqtt_client.publish(
                topic=f'{self.device_id}/response',
                payload='Rebooting device. Please reconnect in ~6 minutes.',
                qos=2,
                retain=False
            )
            os.system("sudo reboot")
            sys.exit(0)

        elif command.startswith("play/"):
            alarm_name = command.split("/", 1)[1]
            alarm_path = f"alarm/{alarm_name}.mp3" 
            self.__add_message_to_queue(f'play/{alarm_name}')
            StatusControl.add_message_to_queue_mqtt(f'play/{alarm_name}')
                
        elif command.startswith("tts/"):
            tts_text = command.split("/", 1)[1]
            self.__add_message_to_queue(f'tts/{tts_text}')
            StatusControl.add_message_to_queue_mqtt(f'tts/{tts_text}')

        elif command == "stop":
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
                Logger.info("Audio playback dihentikan")

        else:
            Logger.warning(f"Unknown command: {command}")

    def __on_subscribe(self, client, userdata, mid, granted_qos, properties=None):
        pass

    # Publish Message
    def publish(self, topic, payload):
        self.mqtt_client.publish(topic=topic, payload=payload, qos=2, retain=False)
    
    def publish_temperature(self):
        _temp_str = "{:.2f}".format(get_temperature()) + "°C"
        Logger.info(_temp_str)
        self.mqtt_client.publish(topic=f'{self.device_id}/temperature', payload=_temp_str, qos=2, retain=False)

    # Get Last Message
    def get_last_msg(self):
        return self.last_msg
    
    # MQTT Loop Forever
    def loop_forever(self):
        self.mqtt_client.loop_forever()

        # Add new client
    def add_new_client(self, username: str)->bool:
        _already_exist = False
        for i in self.list_subscribe:
            if i == username:
                _already_exist = True
                break

        if _already_exist:
            self.mqtt_client.publish(topic=f'{self.device_id}/response', payload=f'{username.capitalize()} is failed to registered. Already exist.', qos=2, retain=False)
            return False
        
        self.list_subscribe.append(username)
        self.mqtt_client.subscribe(f'{username}/unicast', qos=2)
        self.mqtt_client.subscribe(f'{username}/broadcast', qos=2)

        # Write in json file if not exist
        if not self.clients.is_exist(username):
            self.clients.add_client(username)
        
        Logger.info(f'Successfully register {username}')
        return True
    
    # Remove client
    def remove_client(self, username:str):
        if self.is_connect:
            self.mqtt_client.unsubscribe(f'{username}/unicast')
            self.mqtt_client.unsubscribe(f'{username}/broadcast')
            self.clients.remove_client(username)
            for _subs in self.list_subscribe:
                if _subs == username:
                    self.list_subscribe.remove(_subs)

    # Fungsi menambahkan antrian
    def __add_message_to_queue(self, message):
        """Menambahkan pesan ke dalam antrian."""
        if not self.message_queue.full():
            self.message_queue.put(message)  # Menambahkan pesan sebagai list
        else:
            # Jika antrian penuh, hapus pesan pertama
            self.message_queue.get()
            self.message_queue.put(message)  # Menambahkan pesan baru sebagai list
            

    # Response
    async def __responseStatus(self):
            if StatusControl.queueMessage[0]:
                last_queue = StatusControl.queueMessage[1]
                Logger.info(f'Queue : {last_queue}')
                self.mqtt_client.publish(topic=f'{self.device_id}/status/queue', payload=f'Queue : {last_queue}', qos=2, retain=False)
                StatusControl.queueMessage[0] = False

            if not StatusControl.responseQueueDB.empty():
                # Mengambil status dan pesan dari antrian
                message = StatusControl.responseQueueDB.get()
                StatusControl.responseQueueDB.task_done()  # Menandai pesan telah selesai diproses

                _ttsMessage = "None"
                _alarmMessage = "None"
                
                # Publish pesan sesuai dengan jenis perintah
                if message[0] == 'lamp/on':
                    Logger.info("ON")
                    self.mqtt_client.publish(topic=f'{self.device_id}/status/lamp', payload="ON", qos=2, retain=False)
                elif message[0] == 'lamp/off':
                    Logger.info("OFF")
                    self.mqtt_client.publish(topic=f'{self.device_id}/status/lamp', payload="OFF", qos=2, retain=False)
                elif message[0].startswith("tts") and len(message[0].split("/")) > 1 and message[0].split("/")[2] in ["done"]:
                    _ttsMessage = message[0].split("/")[1]
                    if len(_ttsMessage) > 18:
                        _ttsMessage = _ttsMessage[:15] + "..."
                    self.mqtt_client.publish(topic=f'{self.device_id}/status/voice', payload=f'Done : {_ttsMessage}', qos=2, retain=False)
                    Logger.info(f'Done: {_ttsMessage}')
                elif message[0].startswith("alarm") and len(message[0].split("/")) > 1 and message[0].split("/")[1] in ["done"]:
                    _alarmMessage = message[0].split("/")[0]
                    self.mqtt_client.publish(topic=f'{self.device_id}/status/voice', payload=f'Done : {_alarmMessage}.mp3', qos=2, retain=False)
                    Logger.info(f'Done: {_alarmMessage}')
                else:
                    Logger.warning("Status pesan tidak valid.")
            
            if StatusControl.statusMessage[0] == 3:
                _temp_str = "{:.2f}°C".format(get_temperature())
                
                self.mqtt_client.publish(topic=f'{self.device_id}/status/all', payload=f"Lamp:{StatusControl.statusMessage[1]},Player:{StatusControl.statusMessage[2]},Temp:{_temp_str}", qos=2, retain=False)
                StatusControl.statusMessage[0] = 0


    async def __sendLocalMessage(self):
        if not self.message_queue.empty():
            # Mengambil status dan pesan dari antrian
            message = self.message_queue.get()
            self.message_queue.task_done()  # Menandai pesan telah selesai diproses

            # Publish pesan sesuai dengan jenis perintah        
            if 'play' in message:
                _alarmMessage = message.split("/")[1]
                Logger.info(f'Play: {_alarmMessage}')
                self.mqtt_client.publish(topic=f'{self.device_id}/status/voice', payload=f'Play : {_alarmMessage}.mp3', qos=2, retain=False)

            elif 'tts' in message:
                _ttsText = message.split("/")[1]
                if len(_ttsText) > 18:
                    _ttsText = _ttsText[:15] + "..."
                
                Logger.info(f'Play: {_ttsText}')
                
                # 1️⃣ Mainkan opening.mp3 dulu
                opening_path = "tts/opening.mp3"
                if os.path.exists(opening_path):
                    Logger.info("Playing opening.mp3")
                    playsound(opening_path)
                
                # 2️⃣ Generate gTTS dari text
                tts_path = f"tts/{_ttsText}.mp3"
                tts = gTTS(text=_ttsText, lang='en')
                tts.save(tts_path)
                
                # Mainkan hasil gTTS
                Logger.info(f"Playing TTS: {_ttsText}")
                playsound(tts_path)
                
                # Publish status ke MQTT
                self.mqtt_client.publish(
                    topic=f'{self.device_id}/status/voice',
                    payload=f'Done : {_ttsText}',
                    qos=2,
                    retain=False
                )

           
    async def __async_task(self):
        while True:
            await self.__sendLocalMessage()
            await self.__responseStatus()
            await asyncio.sleep(.001)

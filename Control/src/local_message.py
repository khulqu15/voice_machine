import json
import time
import pigpio as pi
from .sys_util import StatusControl, RaspiPin, AudioStatus
# from .sys_util import RaspiPin
from .speech import Speech
from datetime import datetime, time as dtime, timedelta
from src.logger import Logger
import asyncio
from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient
import ast
import os
import re

class LocalMessage:
    def __init__(self):
         # --- Koneksi MongoDB ---
        self.client = AsyncIOMotorClient("mongodb://localhost:27017/")
        self.db = self.client["VoiceAlarmSystem"]
        self.collections_name = ["requests", "responses"]
        self.collections_name_status = ["system_status_res", "system_status_req"]
        self.collections_name_queue = "queue"

        self.read_messages_cache = set()
        self.last_read_timestamp = None

        self.start_time = datetime.now()
        self.timestamp_format = "%a, %d %b %Y %H:%M:%S GMT"
        self.last_check_queue = time.time()

        self.message = "None"
        self.urlset = "None"

        self.tts = False
        self.alarm = False

        self.ttsMsg = "None"
        self.alarmMsg = "None"
        self.stsAlarm = "None"
        self.stsReq = "None"

        self.gpio = RaspiPin()
        self.aS = AudioStatus()
        #  System on the first time
        self.gpio.fan(1)
        self.speech = Speech()
        self.gpio.spk(1)
        self.speech.system_on()
        self.gpio.spk(0)
        # self.gpio.standby(1)

    def main_run(self):
        asyncio.run(self.__async_task())

    def __check_mp3_existence(self, file_name):
        file_name = re.sub(r'[^A-Za-z0-9]', '', file_name)
        directory = os.getcwd()
        
        files = os.listdir(directory + "/assets/alarm")

        for file in files:
            _file = file.lower()
            _target = file_name.lower()
            if (_file == _target or _file == _target + ".mp3") and file.lower().endswith('.mp3'):
                return directory + "/assets/alarm/" + file
        Logger.warning(f"File {file_name} is not exist")
        return False, "No Found"

    # Fungsi untuk memproses pengiriman ke database (All Control)
    async def __send_message_to_database(self, collection_name, pesan, status):
        try:
            collection = self.db[collection_name]
            data = {
                "pesan": pesan,
                "timestamp": datetime.now(),
                "status": status,
            }
            result = await collection.insert_one(data)
        except Exception as e:
            Logger.error(f"Terjadi kesalahan saat mengirim pesan database response: {e}")
    
        # Fungsi untuk memproses pengiriman ke database (Status)
    async def __send_message_to_database_status(self, collection_name, lamp, player, status):
        try:
            collection = self.db[collection_name]
            data = {
                "lamp": lamp,
                "player": player,
                "status": status,
                "timestamp": datetime.now(),
            }
            await collection.insert_one(data)
        except Exception as e:
            Logger.error(f"Terjadi kesalahan saat mengirim pesan database status: {e}")

    # Fungsi untuk memproses pengiriman ke database (Queue)
    async def __send_message_to_database_queue(self, collection_name, pesan):
        try:
            collection = self.db[collection_name]

            filter_query = {}  # Kosong artinya semua data akan diupdate

            update_data = {
                "$set": {
                    "queue": pesan,
                    "timestamp": datetime.now(),
                }
            }

            # update_many -> semua data diupdate, upsert=True -> kalau belum ada, insert baru
            result = await collection.update_many(filter_query, update_data, upsert=True)

            if result.matched_count > 0:
                Logger.info(f"{result.modified_count} data di '{collection_name}' berhasil diupdate.")
            else:
                Logger.info(f"Data baru dimasukkan ke '{collection_name}' (upsert).")

        except Exception as e:
            Logger.error(f"Terjadi kesalahan saat mengirim pesan update queue: {e}")

   # Fungsi untuk memproses dan menandai pesan yang sudah dibaca
    async def __readMulti_process_messages(self):
        try:
            col = self.db[self.collections_name[0]]

            cursor = col.find({"timestamp": {"$gt": self.start_time}})
            messages = await cursor.to_list(length=None)
            messages.sort(key=lambda x: x['timestamp'])

            for message in messages:
                msg_id = str(message["_id"])
                if msg_id not in self.read_messages_cache:

                    if message['status'] in ["mqtt", "local"] and (
                        message['pesan'] in ["on", "off"] or
                        message['pesan'].startswith("tts/") or
                        message['pesan'].startswith("play/")
                    ):
                        StatusControl.add_message_to_queue_dbr({
                            "status": message['status'],
                            "pesan": message['pesan']  # Pastikan selalu string
                        })

                    self.read_messages_cache.add(msg_id)
                    # await col.delete_one({"_id": message["_id"]})

        except Exception as e:
            Logger.error(f"[ERROR] Gagal membaca collections: {e}")
            await asyncio.sleep(1)  # Delay jika error supaya tidak terlalu cepat retry

    
    # Fungsi untuk memproses pembacaa sekali
    async def __readSingle_process_messages(self):
        try:
            if (StatusControl.statusMessage[0] == False):
                col = self.db[self.collections_name_status[1]]

                cursor = col.find({"timestamp": {"$gt": self.start_time}})
                messages = await cursor.to_list(length=None)
                messages.sort(key=lambda x: x['timestamp'])

                for message in messages:
                    msg_id = str(message["_id"])
                    if msg_id not in self.read_messages_cache:

                        if message['status'] in ["mqtt", "local"]:
                            StatusControl.statusMessage[0] = True
                            StatusControl.statusMessage[1] = message['status']

                        self.read_messages_cache.add(msg_id)
                        # await col.delete_one({"_id": message["_id"]})

        except Exception as e:
            Logger.error(f"[ERROR] Gagal membaca collections one: {e}")
            await asyncio.sleep(1)  # Delay jika error supaya tidak terlalu cepat retry
    
    def __extract_status_pesan(self,message):
        while isinstance(message, (list, tuple)) and len(message) > 0:
            message = message[0]

        if isinstance(message, dict):
            status = message.get('status')
            pesan = message.get('pesan')
        else:
            status = None
            pesan = message

        return status, str(pesan) if pesan is not None else ""


    # Response
    async def __responseStatus(self):
        if not StatusControl.responseQueueDBR.empty():
            message = StatusControl.responseQueueDBR.get()
            StatusControl.responseQueueDBR.task_done()

            status, pesan = self.__extract_status_pesan(message)

            if pesan == "on":
                Logger.info(f"Lamp ON (status: {status})")
                self.gpio.lamp(1)
                StatusControl.add_message_to_queue_dbw([{
                    "status": status,
                    "pesan": "lamp/on"
                }])

            elif pesan == "off":
                Logger.info(f"Lamp OFF (status: {status})")
                self.gpio.lamp(0)
                StatusControl.add_message_to_queue_dbw([{
                    "status": status,
                    "pesan": "lamp/off"
                }])

            elif pesan.startswith("tts/"):
                _t = pesan.split("/", 1)
                if len(_t) > 1:
                    self.ttsMsg = _t[1]
                    self.stsReq = status
                Logger.info(f"TTS Play: {_t[1]} (status: {status})")
                self.tts = True

            elif pesan.startswith("play/"):
                _a = pesan.split("/", 1)
                if len(_a) > 1:
                    self.alarmMsg = self.__check_mp3_existence(_a[1])
                    self.stsAlarm = _a[1]
                    self.stsReq = status
                Logger.info(f"Alarm Play: {_a[1]} (status: {status})")
                self.alarm = True
            else:
                Logger.warning(f"Pesan bukan string, isi: {pesan}")

    async def __tts_async(self):
        if(self.tts):
            _send_word = self.ttsMsg
            self.gpio.spk(1)
            await asyncio.sleep(1.5)
            
            StatusControl.add_message_to_queue_dbw({
                            "status": self.stsReq,
                            "pesan": f'tts/{_send_word}/play'
                        })
            Logger.info(f'Play : {_send_word}')

            if not self.speech.text_to_speech(_send_word):
                Logger.error(f'Failed : {_send_word}')
            else:
                Logger.info(f'Done : {_send_word}')
                StatusControl.add_message_to_queue_dbw({
                            "status": self.stsReq,
                            "pesan": f'tts/{_send_word}/done'
                        })
            self.gpio.spk(0)
            self.tts = False

    # Fungsi untuk play alarm
    async def __alarm_async(self):
        if(self.alarm):
            _path = self.alarmMsg 
            self.gpio.spk(1)
            await asyncio.sleep(1.5)
            StatusControl.add_message_to_queue_dbw({
                            "status": self.stsReq,
                            "pesan": f'{self.stsAlarm}/play'
                        })
            Logger.info(f'Play : {_path}')
            
            self.speech.play_alarm(_path)
            self.gpio.spk(0)
            StatusControl.add_message_to_queue_dbw({
                            "status": self.stsReq,
                            "pesan": f'{self.stsAlarm}/done'
                        })
            Logger.info(f'Done : {_path}')
            self.alarm = False

    # Fungsi untuk menulis pesan baru
    async def __write_process_message(self):
        if time.time() - self.last_check_queue > 115:
            queue = StatusControl.responseQueueDBW.qsize()
            await self.__send_message_to_database_queue(self.collections_name_queue, queue)
            self.last_check_queue = time.time()

        if not StatusControl.responseQueueDBW.empty():
            message = StatusControl.responseQueueDBW.get()

            status, pesan = self.__extract_status_pesan(message)
            
            await self.__send_message_to_database(self.collections_name[1], pesan, status)

            StatusControl.responseQueueDBW.task_done()

        if StatusControl.statusMessage[0]:
            status = StatusControl.statusMessage[1]
            if self.gpio.statusLamp() == 1:
                statusLamp = "ON"
            else:
                statusLamp = "OFF"

            if self.aS.is_audio_in_use():
                statusAudio = "Busy"
            else:
                statusAudio = "Free"

            Logger.info(f"Status Lamp: {statusLamp}, Status Audio: {statusAudio}, Status: {status}")
            await self.__send_message_to_database_status(self.collections_name_status[0], statusLamp, statusAudio, status)
            StatusControl.statusMessage[0] = False
            
    async def __clear_collections(self):
        total_deleted = 0
        for col_name in self.collections_name + self.collections_name_status:
            collection = self.db[col_name]
            result = await collection.delete_many({})
            Logger.info(f"[{datetime.now()}] Collection '{col_name}' dihapus {result.deleted_count} dokumen.")
            total_deleted += result.deleted_count
        return total_deleted
    
    async def __schedule_clear(self):
        now = datetime.now()
        if now.hour == 0 and now.minute == 0 and (now.second >= 0 and now.second <= 5):
            await self.__clear_collections()
            await asyncio.sleep(1)
            
    async def __restartService(self):
        if  self.gpio.rstService() == 0:
            await self.__clear_collections()
            await asyncio.sleep(1)
            Logger.info("Restarting Services...")
            os.system("sudo systemctl restart mqtt.service")
            os.system("sudo systemctl restart server.service")
            os.system("sudo systemctl restart monitor.service")

    async def __async_task(self):
        while True:
            await self.__schedule_clear()
            await self.__readSingle_process_messages()
            await self.__readMulti_process_messages()
            await self.__responseStatus()
            await self.__write_process_message()
            await self.__tts_async()
            await self.__alarm_async()
            await self.__restartService()
            await asyncio.sleep(.001)

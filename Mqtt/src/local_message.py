from .sys_util import StatusControl
from datetime import datetime
import asyncio
from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient
import queue
from src.logger import Logger

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

        self.message = "None"

    def main_run(self):
        # Jalankan async task utama
        asyncio.run(self.__async_task())

    # Fungsi untuk memproses pengiriman ke database
    async def __send_message_to_database(self, collection_name, pesan, status="mqtt"):
        try:
            collection = self.db[collection_name]
            data = {
                "pesan": pesan,
                "timestamp": datetime.now(),
                "status": status,
            }
            await collection.insert_one(data)
            Logger.info(f"Data disimpan ke '{collection_name}'")
        except Exception as e:
            Logger.error(f"Terjadi kesalahan saat mengirim pesan: {e}")

    async def __send_message_to_database_status_req(self, collection_name, status):
        try:
            collection = self.db[collection_name]
            data = {
                "status": status,
                "timestamp": datetime.now(),
            }
            await collection.insert_one(data)
            Logger.info(f"Data disimpan ke '{collection_name}'")
        except Exception as e:
            Logger.error(f"Terjadi kesalahan saat mengirim pesan: {e}")

    # Fungsi untuk memproses dan menandai pesan yang sudah dibaca
    async def __readMulti_process_messages(self):
        try:
            col = self.db[self.collections_name[1]]

            cursor = col.find({"timestamp": {"$gt": self.start_time}})
            messages = await cursor.to_list(length=None)
            messages.sort(key=lambda x: x['timestamp'])

            for message in messages:
                msg_id = str(message["_id"])
                if msg_id not in self.read_messages_cache:

                    if message['status'] == 'mqtt' and (
                        message['pesan'] in ["lamp/on", "lamp/off"] or
                        (message['pesan'].startswith("alarm") and
                            len(message['pesan'].split("/")) > 1 and
                            message['pesan'].split("/")[1] in ["done"]) or
                        (message['pesan'].startswith("tts/") and
                            len(message['pesan'].split("/")) > 2 and
                            message['pesan'].split("/")[2] in ["done"])
                    ):
                        StatusControl.add_message_to_queue_db(message['pesan'])

                    self.read_messages_cache.add(msg_id)
                    # await col.delete_one({"_id": message["_id"]})
        except Exception as e:
            Logger.error(f"[ERROR] Gagal membaca collections: {e}")
            await asyncio.sleep(1)  # Delay jika error supaya tidak terlalu cepat retry

    # Fungsi untuk memproses pembacaan sekali
    async def __readSingle_process_messages(self):
        try:
            if (StatusControl.statusMessage[0] == 2):
                col = self.db[self.collections_name_status[0]]

                cursor = col.find({"timestamp": {"$gt": self.start_time}})
                messages = await cursor.to_list(length=None)
                messages.sort(key=lambda x: x['timestamp'])

                for message in messages:
                    msg_id = str(message["_id"])
                    if msg_id not in self.read_messages_cache:
                        if message['status'] in ["mqtt"]:
                            StatusControl.statusMessage[0] = 3
                            StatusControl.statusMessage[1] = message['lamp']
                            StatusControl.statusMessage[2] = message['player']
                        
                        self.read_messages_cache.add(msg_id)
                        # await col.delete_one({"_id": message["_id"]})

        except Exception as e:
            Logger.error(f"[ERROR] Gagal membaca collections: {e}")
            await asyncio.sleep(1)  # Delay jika error supaya tidak terlalu cepat retry

    async def __readQueue_process_messages(self):
        try:
            col = self.db[self.collections_name_queue]

            # Ambil pesan dengan timestamp lebih baru dari start_time terakhir
            cursor = col.find({"timestamp": {"$gt": self.start_time}})
            messages = await cursor.to_list(length=None)
            messages.sort(key=lambda x: x['timestamp'])

            for message in messages:
                StatusControl.queueMessage = [True, message['queue']]

            # Update start_time ke timestamp pesan terakhir yang dibaca
            if messages:
                self.start_time = messages[-1]['timestamp']

        except Exception as e:
            Logger.error(f"[ERROR] Gagal membaca collections: {e}")
            await asyncio.sleep(1)  # Delay jika error supaya tidak terlalu cepat retry

    # Fungsi untuk menulis pesan baru
    async def __write_process_message(self):
        if not StatusControl.responseQueueMqtt.empty():
            message = StatusControl.responseQueueMqtt.get()

            await self.__send_message_to_database(self.collections_name[0], message[0])

            StatusControl.responseQueueMqtt.task_done()

        if StatusControl.statusMessage[0] == 1:
            StatusControl.statusMessage[0] = 2
            await self.__send_message_to_database_status_req(self.collections_name_status[1], "mqtt")
    
    async def __async_task(self):
        while True:
            await self.__readMulti_process_messages()
            await self.__readSingle_process_messages()
            await self.__readQueue_process_messages()
            await self.__write_process_message()
            await asyncio.sleep(.001)


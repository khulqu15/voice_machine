from flask import Flask, request, jsonify
from pymongo import MongoClient
import datetime  # Impor modul datetime
import time
import configparser

config = configparser.ConfigParser()
config.read('vas.config')

valid_api_key = config["security"]["valid_api_key"]
port = int(config["server"]["port"])
debug_mode = config["server"].getboolean("debug")

# Inisialisasi aplikasi Flask
app = Flask(__name__)

# Koneksi ke MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["VoiceAlarmSystem"]

# Koleksi yang akan digunakan (status sudah dihapus)
collections1 = ["requests", "responses"]
collections2 = ["system_status_req", "system_status_res", "queue"]

# Daftar klien yang sedang menunggu data baru
waiting_clients = []

# Untuk menyimpan ID pesan yang sudah dibaca
read_messages_cache = set()

# Fungsi untuk menyimpan pesan ke dalam koleksi yang sesuai
def store_message(collection_name, message, status="local"):  # Tambahkan parameter status
    collection = db[collection_name]
    timestamp = datetime.datetime.now()  # Mengambil waktu UTC saat ini
    data = {"pesan": message, "timestamp": timestamp, "status": status}  # Menambahkan status ke dalam data pesan
    try:
        collection.insert_one(data)
          
        # # cek jumlah data
        # count = collection.count_documents({})
        # if count > 10:
        #     # hapus pesan lama, sisakan 10 terbaru
        #     oldest = collection.find().sort("timestamp", 1).limit(count - 10)
        #     ids_to_delete = [doc["_id"] for doc in oldest]
        #     collection.delete_many({"_id": {"$in": ids_to_delete}})

        return True, None
    except Exception as e:
        return False, str(e)

# Fungsi untuk menyimpan pesan ke dalam koleksi status device
def store_message_status_device(collection_name, pesan, status="local"):
    collection = db[collection_name]

    # Cek apakah pesan mengandung field "status"
    if "status" not in pesan:
        return False, "Field 'status' tidak ditemukan dalam pesan."

    try:
        # Buat data yang akan disimpan, termasuk timestamp
        data = {
            "timestamp": datetime.datetime.now(),
            "status": status
        }

        # collection.insert_one(data)
        #   # cek jumlah data
        # count = collection.count_documents({})
        # if count > 10:
        #     # hapus pesan lama, sisakan 10 terbaru
        #     oldest = collection.find().sort("timestamp", 1).limit(count - 10)
        #     ids_to_delete = [doc["_id"] for doc in oldest]
        #     collection.delete_many({"_id": {"$in": ids_to_delete}})
            
        return True, None
    except Exception as e:
        return False, str(e)


# Fungsi untuk membaca semua pesan dari koleksi yang sesuai
def get_all_messages(collection_name):
    collection = db[collection_name]
    try:
        messages = list(collection.find({}, {"_id": 0, "pesan": 1, "timestamp": 1, "status": 1}))  # Mengambil semua pesan dan status
        return messages, None
    except Exception as e:
        return None, str(e)

# Fungsi untuk membaca 10 pesan terbaru dari koleksi yang sesuai
def get_latest_messages(collection_name, limit=10):
    collection = db[collection_name]
    try:
        messages = list(collection.find({}, {"_id": 0, "pesan": 1, "timestamp": 1, "status": 1}).sort([("timestamp", -1)]).limit(limit))  # Mengambil 10 pesan terbaru
        return messages, None
    except Exception as e:
        return None, str(e)
    
# Fungsi untuk membaca maksimal 10 pesan terbaru dari koleksi yang ada dengan status 'local'
def get_latest_messages_from_multiple_collections(limit=10):
    latest_messages = []

    # Memeriksa setiap koleksi untuk pesan terbaru
    for collection_name in collections1:
        collection = db[collection_name]
        messages = list(collection.find(
                            {
                                "_id": {"$nin": list(read_messages_cache)},
                                "status": "local"  # Filter hanya status local
                            }
                        )
                        .sort([('timestamp', -1)])  # Urutkan berdasarkan timestamp terbaru
                        .limit(limit))  # Batasi jumlah pesan

        for message in messages:
            read_messages_cache.add(str(message["_id"]))  # Hindari duplikasi
            latest_messages.append({
                "collection": collection.name,
                "pesan": message.get("pesan"),
                "status": message.get("status"),
                "timestamp": message.get("timestamp"),
                "id": str(message["_id"])
            })

    # Urutkan seluruh pesan berdasarkan timestamp dan batasi total pesan
    latest_messages.sort(key=lambda x: x["timestamp"], reverse=True)
    return latest_messages[:limit]


# CREATE: Menyimpan pesan ke koleksi yang ditentukan
@app.route('/create/<collection_name>', methods=['POST'])
def create_data(collection_name):
    # Cek API Key yang dikirim melalui header
    api_key = request.headers.get('API-Key')
    if api_key != valid_api_key:
        return jsonify({"error": "API Key tidak valid!"}), 403

    # Cek apakah collection yang diminta valid
    if collection_name not in collections1:
        return jsonify({"error": "Koleksi tidak valid!"}), 400

    # Mendapatkan data JSON yang dikirim dalam request
    data = request.get_json()

    # Cek apakah pesan ada dalam data
    if "pesan" not in data:
        return jsonify({"error": "Pesan tidak ditemukan dalam data!"}), 400

    message = data["pesan"]
    success, error = store_message(collection_name, message)

    if success:
        return jsonify({"message": "Pesan berhasil disimpan!"}), 201
    else:
        return jsonify({"error": f"Terjadi kesalahan: {error}"}), 500

# CREATE: Menyimpan pesan ke koleksi status device
@app.route('/create/status', methods=['POST'])
def create_data_status():
    api_key = request.headers.get('API-Key')
    if api_key != valid_api_key:
        return jsonify({"error": "API Key tidak valid!"}), 403

    data = request.get_json()

    if "pesan" not in data:
        return jsonify({"error": "Field 'pesan' tidak ditemukan dalam data!"}), 400

    message = data["pesan"]

    success, error = store_message_status_device(collections2[0], message)

    if success:
        return jsonify({"message": "Pesan berhasil disimpan!"}), 201
    else:
        return jsonify({"error": f"Terjadi kesalahan: {error}"}), 500

    
# READ: Membaca pesan berdasarkan tipe yang diminta (semua pesan atau 10 terbaru)
@app.route('/read/<collection_name>', methods=['GET'])
def read_data(collection_name):
    # Cek API Key yang dikirim melalui header
    api_key = request.headers.get('API-Key')
    if api_key != valid_api_key:
        return jsonify({"error": "API Key tidak valid!"}), 403

    # Cek apakah collection yang diminta valid
    if collection_name not in collections1:
        return jsonify({"error": "Koleksi tidak valid!"}), 400

    # Mendapatkan parameter tipe dan limit dari query string
    message_type = request.args.get('type', 'latest')  # Default ke 'latest' (10 pesan terbaru)
    
    # Untuk 'all' ambil semua pesan, untuk 'latest' ambil 10 pesan terbaru
    if message_type == 'all':
        messages, error = get_all_messages(collection_name)
    elif message_type == 'latest':
        messages, error = get_latest_messages(collection_name, limit=10)
    else:
        return jsonify({"error": "Tipe pesan tidak valid. Gunakan 'all' atau 'latest'."}), 400

    if messages is not None:
        return jsonify({"messages": messages}), 200
    else:
        return jsonify({"error": f"Terjadi kesalahan: {error}"}), 500

# READ: Mengambil pesan terbaru dari koleksi yang ada dan memilih yang terbaru (10 pesan terbaru)
@app.route('/read/latest', methods=['GET'])
def read_latest_from_multiple():
    # Cek API Key yang dikirim melalui header
    api_key = request.headers.get('API-Key')
    if api_key != valid_api_key:
        return jsonify({"error": "API Key tidak valid!"}), 403

    # Mengambil 10 pesan terbaru dari beberapa koleksi
    latest_messages = get_latest_messages_from_multiple_collections(limit=10)

    if latest_messages:
        return jsonify({"messages": latest_messages}), 200
    else:
        return jsonify({"error": "Tidak ada pesan baru yang ditemukan."}), 404

# READ: Mengambil pesan terbaru dari koleksi status
@app.route('/read/status', methods=['GET'])
def read_system_status():
    api_key = request.headers.get('API-Key')
    if api_key != valid_api_key:
        return jsonify({"error": "API Key tidak valid!"}), 403

    try:
        # Ambil collection dari database
        status_collection = db[collections2[1]]

        # Ambil 1 data terbaru dengan status=local
        cursor = status_collection.find(
            {"status": "local"},  # filter status untuk validasi
            {"_id": 0, "status": 0}  # sembunyikan field 'status' di response
        ).sort("timestamp", -1).limit(1)

        message = list(cursor)
        if message:
            return jsonify({"message": message[0]}), 200
        else:
            return jsonify({"error": "Tidak ada status 'local' yang ditemukan."}), 404

    except Exception as e:
        return jsonify({"error": f"Gagal membaca status: {str(e)}"}), 500

    
# READ: Mengambil pesan terbaru dari koleksi queue
@app.route('/read/queue', methods=['GET'])
def read_system_queue():
    api_key = request.headers.get('API-Key')
    if api_key != valid_api_key:
        return jsonify({"error": "API Key tidak valid!"}), 403

    try:
        # Ambil collection dari database
        status_collection = db[collections2[2]]

        cursor = status_collection.find({}, {"_id": 0})

        message = list(cursor)
        if message:
            return jsonify({"messages": message}), 200
        else:
            return jsonify({"error": "Tidak ada queue yang ditemukan."}), 404

    except Exception as e:
        return jsonify({"error": f"Gagal membaca queue: {str(e)}"}), 500


# Menjalankan server Flask
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port, debug=debug_mode)

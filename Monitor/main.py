import subprocess
import time
import requests
import socket
from datetime import datetime
import os
import queue
import threading

# === KONFIGURASI ===
SERVICE_NAME = "mqtt.service"
DEVICE_NAME = "VAS1"
CHECK_INTERVAL = 10  # detik
NOTIF_TIMEOUT = 10  # detik

#Telegram
TELEGRAM_TOKEN = "xxxxxx"
CHAT_ID = "xxxxxxx"

_log_directory = 'logs'
pending_messages = []

#Antrian
pending_messages = queue.Queue()

# === CEK INTERNET ===
def is_connected(host="8.8.8.8", port=53, timeout=5):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error:
        return False

# === LOGGING ===
def get_log_filename():
    today = datetime.now().strftime("%Y-%m-%d")
    return os.path.join(_log_directory, f"monitor_{today}.txt")

def write_log(message):
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    full_message = f"{timestamp} {message}"
    print(full_message)
    
    if not os.path.exists(_log_directory):
        os.makedirs(_log_directory)
        
    with open(get_log_filename(), "a") as f:
        f.write(full_message + "\n")

# === Telegram functions ===
def send_telegram(message, from_queue=False):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        write_log("[TELEGRAM] TOKEN atau CHAT_ID belum diisi!")
        return False

    if not is_connected():
        write_log(f"[JARINGAN] OFFLINE - Menyimpan pesan Telegram: {message}")
        if not from_queue:
            pending_messages.put(message)
        return False

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": message}
        requests.post(url, data=payload, timeout=20)
        write_log(f"[TELEGRAM] Terkirim: {message}")
        return True
    except Exception as e:
        write_log(f"[ERROR] Gagal kirim Telegram: {e}")
        if not from_queue:
            pending_messages.put(message)
        return False

def resend_pending_messages():
    if pending_messages.empty():
        return
    if not is_connected():
        write_log("[JARINGAN] Masih offline, tunggu sebelum kirim pesan Telegram tertunda...")
        return
    write_log(f"[QUEUE] Mencoba kirim ulang {pending_messages.qsize()} pesan Telegram tertunda...")
    still_pending = []
    while not pending_messages.empty():
        msg = pending_messages.get()
        success = send_telegram(msg, from_queue=True)
        if not success:
            still_pending.append(msg)
        time.sleep(1)
    for msg in still_pending:
        pending_messages.put(msg)

# === Background worker thread ===
def background_worker():
    while True:
        resend_pending_messages()
        time.sleep(10)

# === CEK STATUS SERVICE ===
def get_service_status(service):
    try:
        output = subprocess.check_output(["systemctl", "is-active", service], text=True).strip()
        return output
    except subprocess.CalledProcessError:
        return "inactive"

# === RESTART SERVICE ===
def restart_service(service):
    try:
        subprocess.run(["sudo", "systemctl", "restart", service], check=True)
        return True
    except subprocess.CalledProcessError:
        return False

# === MONITOR UTAMA ===
def monitor_service():
    write_log(f"Memulai monitoring service: {SERVICE_NAME}")
    last_status = None
    inactive_start_time = None
    notified_inactive = True
    
    threading.Thread(target=background_worker, daemon=True).start()

    while True:
        status = get_service_status(SERVICE_NAME)
        current_time = time.time()


        # Log perubahan status service
        if status != last_status:
            write_log(f"[STATUS] {SERVICE_NAME} berubah jadi {status.upper()}")
            if status == "active":
                if notified_inactive:
                    send_telegram(f"[INFO] Status {DEVICE_NAME}: ACTIVE")
                    notified_inactive = False
            elif status in ["inactive", "failed"]:
                inactive_start_time = current_time
            last_status = status
			
        # Tangani kondisi mati
        if status in ["inactive", "failed"]:
            if inactive_start_time and (current_time - inactive_start_time) >= NOTIF_TIMEOUT:
                send_telegram(f"[INFO] Status {DEVICE_NAME}: Device Tidak Dapat Dipulihkan. Status Mqtt-OFF")
                write_log(f"[INFO] Status {DEVICE_NAME}: Device Tidak Dapat Dipulihkan. Status Mqtt-OFF")
                inactive_start_time = None
                notified_inactive = True
        else:
            inactive_start_time = None


        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    monitor_service()


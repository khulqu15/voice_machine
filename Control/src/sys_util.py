import psutil
import socket
import getpass
import queue
import pigpio
import os
import pigpio
import subprocess

class RaspiPin:
    def __init__(self):        
        self.pi = pigpio.pi()
        if not self.pi.connected:
            raise RuntimeError("Tidak bisa terhubung ke pigpiod")

        # Definisikan pin GPIO Anda
        self.fan_pin = 23
        self.speaker_pin = 24
        self.lamp_pin = 25
        self.standby_pin = 17
        self.restart_pin = 12

        # Set mode semua pin sebagai output
        self.pi.set_mode(self.fan_pin, pigpio.OUTPUT)
        self.pi.set_mode(self.lamp_pin, pigpio.OUTPUT)
        self.pi.set_mode(self.speaker_pin, pigpio.OUTPUT)
        self.pi.read(self.lamp_pin)
        self.pi.set_mode(self.restart_pin, pigpio.INPUT)

    def fan(self, logic):
        self.pi.write(self.fan_pin, logic)

    def lamp(self, logic):
        self.pi.write(self.lamp_pin, logic)

    def spk(self, logic):
        self.pi.write(self.speaker_pin, logic)
    
    def statusLamp(self):
        return self.pi.read(self.lamp_pin)
    
    def standby(self, logic):
        self.pi.write(self.standby_pin, logic)
        
    def rstService(self):
        return self.pi.read(self.restart_pin)
        
    def cleanup(self):
        self.pi.stop()  # Tutup koneksi pigpio jika sudah tidak digunakan

class AudioStatus:
    def is_audio_in_use(self):
        try:
            # Cek proses yang memegang perangkat audio
            output = subprocess.check_output("lsof /dev/snd/*", shell=True, stderr=subprocess.DEVNULL)
            if output:
                return True
        except subprocess.CalledProcessError:
            return False
        return False

class StatusControl:
    statusMessage = [False, "None"]

    responseQueueDBR = queue.Queue(maxsize=50)  # Inisialisasi responseQueueDB sebagai antrian
    responseQueueDBW = queue.Queue(maxsize=50)  # Inisialisasi responseQueueMQTT sebagai antrian

    @classmethod
    def add_message_to_queue_dbr(cls, message):
        """Menambahkan pesan ke dalam antrian."""
        if not cls.responseQueueDBR.full():
            cls.responseQueueDBR.put([message])  # Menambahkan pesan sebagai list
        else:
            # Jika antrian penuh, hapus pesan pertama
            cls.responseQueueDBR.get()
            cls.responseQueueDBR.put([message])  # Menambahkan pesan baru sebagai list
    
    @classmethod
    def add_message_to_queue_dbw(cls, message):
        """Menambahkan pesan ke dalam antrian."""
        if not cls.responseQueueDBW.full():
            cls.responseQueueDBW.put([message])  # Menambahkan pesan sebagai list
        else:
            # Jika antrian penuh, hapus pesan pertama
            cls.responseQueueDBW.get()
            cls.responseQueueDBW.put([message])  # Menambahkan pesan baru sebagai list

# Generate a list of dictionaries containing network interface names and their corresponding IPv4 addresses.
def get_ip_addresses() -> list:
    addresses = {}
    all_ip = []
    
    interfaces = psutil.net_if_addrs()
    for iface_name, iface_addrs in interfaces.items():
        for addr in iface_addrs:
            if addr.family == socket.AF_INET:  # IPv4 addresses only
                if iface_name not in addresses:
                    addresses[iface_name] = []
                addresses[iface_name].append(addr.address)

    for iface_name, iface_addrs in addresses.items():
        if "eth" in iface_name.lower() or "wlan" in iface_name.lower() or "en" in iface_name.lower():
            all_ip.append({'connection': iface_name, 'ip':  iface_addrs})
    return all_ip

# Get the host information by retrieving the current username.
def get_host() -> str:
    username = getpass.getuser()
    return username

# Get the temperature from CPUTemperature and return it as a float.
def get_temperature()->float:
    temp = psutil.sensors_temperatures()
    if 'cpu_thermal' in temp:
        return temp['cpu_thermal'][0].current
    return None

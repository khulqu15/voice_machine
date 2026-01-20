import psutil
import socket
import getpass
import queue
import os

class StatusControl:
    statusMessage = [0, "None", "None"]
    queueMessage = [False, 0]

    responseQueueDB = queue.Queue(maxsize=20)  # Inisialisasi responseQueueDB sebagai antrian
    responseQueueMqtt = queue.Queue(maxsize=20)  # Inisialisasi responseQueueMQTT sebagai antrian

    @classmethod
    def add_message_to_queue_db(cls, message):
        """Menambahkan pesan ke dalam antrian."""
        if not cls.responseQueueDB.full():
            cls.responseQueueDB.put([message])  # Menambahkan pesan sebagai list
        else:
            # Jika antrian penuh, hapus pesan pertama
            cls.responseQueueDB.get()
            cls.responseQueueDB.put([message])  # Menambahkan pesan baru sebagai list
    
    @classmethod
    def add_message_to_queue_mqtt(cls, message):
        """Menambahkan pesan ke dalam antrian."""
        if not cls.responseQueueMqtt.full():
            cls.responseQueueMqtt.put([message])  # Menambahkan pesan sebagai list
        else:
            # Jika antrian penuh, hapus pesan pertama
            cls.responseQueueMqtt.get()
            cls.responseQueueMqtt.put([message])  # Menambahkan pesan baru sebagai list


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
w
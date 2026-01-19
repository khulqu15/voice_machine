import requests
import time

# Checks the connection by sending a GET request to 'https://console.hivemq.cloud' with a timeout of 3 seconds.
def check_connection():
    try:
        requests.get('https://dns.google/', timeout=3)
        return True
    except requests.ConnectionError:
        return False
    except requests.ReadTimeout:
        return False

# Check the connection asynchronously and return True if successful, False otherwise.
async def check_connection_async():
	try:
		requests.get('https://dns.google/', timeout=3)
		return True
	except requests.ConnectionError:
		return False

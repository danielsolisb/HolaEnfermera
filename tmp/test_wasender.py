import os
import sys
import requests
import json
from pathlib import Path

# Add project path to sys.path
sys.path.append(r"c:\Users\danie\Documents\PROYECTOS_PROG\HOLAENFERMERA\HolaEnfermera")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from django.conf import settings

api_key = settings.WASENDERAPI_API_KEY
headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json',
}

# we can try to hit get-all-contacts
print("Testing GET /api/contacts")
url = "https://wasenderapi.com/api/contacts"
try:
    resp = requests.get(url, headers=headers, timeout=10)
    print("Status:", resp.status_code)
    data = resp.json()
    print("Keys in response:", data.keys())
    if 'data' in data and isinstance(data['data'], list):
        print("Total contacts:", len(data['data']))
        # find the one with LID 219210852626532
        for c in data['data']:
            if '219210852626532' in str(c):
                print("FOUND LID in contacts:", c)
except Exception as e:
    print("Error:", e)

print("-----")
# Let's see if we can get-contact-info with POST
url2 = "https://wasenderapi.com/api/contacts/get-contact-info"
payload = {"jid": "219210852626532@lid"}
try:
    resp2 = requests.post(url2, headers=headers, json=payload, timeout=10)
    print("Status url2 POST:", resp2.status_code)
    print("Resp2:", resp2.text)
except Exception as e:
    print("Error:", e)
    
try:
    resp2_get = requests.get(url2, headers=headers, params={"jid": "219210852626532@lid"}, timeout=10)
    print("Status url2 GET:", resp2_get.status_code)
    print("Resp2 GET:", resp2_get.text)
except Exception as e:
    print("Error:", e)

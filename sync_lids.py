import os
import sys
import requests

sys.path.append(r"c:\Users\danie\Documents\PROYECTOS_PROG\HOLAENFERMERA\HolaEnfermera")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from CoreApps.chat.views import WasenderWebhookView
from django.conf import settings

api_key = settings.WASENDERAPI_API_KEY
headers = {'Authorization': f'Bearer {api_key}'}

print("Fetching contacts from WASender...")
resp = requests.get("https://wasenderapi.com/api/contacts", headers=headers, timeout=30)
data = resp.json().get('data', [])

print(f"Syncing {len(data)} contacts to populate whatsapp_lid...")
view = WasenderWebhookView()
view._handle_contact_sync(data)
print("Sync complete.")

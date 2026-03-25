import requests
import json

api_key = "0b4ab53a3e5d363187985f206e8bb88ce2470e736fdd9d93a21fb83701b8a0c6"
headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}

lid = "219210852626532@lid" # Stefy

print(f"=== Investigando chat para LID: {lid} ===")
try:
    resp = requests.get("https://wasenderapi.com/api/chats", headers=headers, timeout=15)
    data = resp.json().get('data', [])
    print(f"Total chats: {len(data)}")
    for chat in data:
        if '219210852626532' in chat.get('id', ''):
            print("FOUND CHAT BY ID!")
            print(json.dumps(chat, indent=2))
            break
except Exception as e:
    print("Error fetching chats:", e)

# also check if there is an endpoint for chat messages
try:
    print("--- Fetching specific chat messages ---")
    url = f"https://wasenderapi.com/api/chats/{lid}/messages"
    resp = requests.get(url, headers=headers, timeout=15)
    print("Status:", resp.status_code)
    msgs = resp.json().get('data', [])[:3]
    print(json.dumps(msgs, indent=2))
except Exception as e:
    print("Error:", e)

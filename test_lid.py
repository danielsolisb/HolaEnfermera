import requests
import json

api_key = "0b4ab53a3e5d363187985f206e8bb88ce2470e736fdd9d93a21fb83701b8a0c6"
headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json',
}

url = "https://wasenderapi.com/api/contacts"
print("Testing URL GET:", url)
try:
    resp = requests.get(url, headers=headers, timeout=10)
    print("Status:", resp.status_code)
    data = resp.json()
    
    if data.get('success'):
        print(f"Got {len(data.get('data', []))} contacts.")
        for msg in data.get('data', []):
            # msg is usually a dict
            if '219210852626532' in str(msg):
                print("FOUND LID IN CONTACTS!:", json.dumps(msg, indent=2))
        
        # also let's print the first 2 contacts just to see their structure
        print("Sample contacts:")
        print(json.dumps(data.get('data', [])[:2], indent=2))
    else:
        print("API error:", data)
except Exception as e:
    print("Error GET:", e)

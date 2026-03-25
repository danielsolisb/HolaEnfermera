import requests
import json
import time

# Configuración
BASE_URL = "http://127.0.0.1:8000"
WEBHOOK_URL = f"{BASE_URL}/chat/webhook/wasender/"
# Este secreto debe coincidir con el de tu .env
WEBHOOK_SECRET = "8c643bb4b0f3c2cec8fa4c81cb62c2ee"

def send_mock_webhook(phone, text, push_name="Cliente de Prueba"):
    payload = {
        "event": "messages.upsert",
        "timestamp": int(time.time()),
        "data": {
            "messages": [
                {
                    "key": {
                        "id": f"mock_msg_{int(time.time())}_{phone}",
                        "fromMe": False,
                        "remoteJid": f"{phone}@s.whatsapp.net"
                    },
                    "pushName": push_name,
                    "message": {
                        "conversation": text
                    }
                }
            ]
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": WEBHOOK_SECRET
    }
    
    print(f"Probando mensaje desde: {phone} - '{text}'...")
    try:
        response = requests.post(WEBHOOK_URL, json=payload, headers=headers)
        print(f"Respuesta del servidor: {response.status_code}")
        print(response.json())
    except Exception as e:
        print(f"Error en la conexión: {e}")

if __name__ == "__main__":
    print("--- SIMULADOR DE WEBHOOK WASENDER (PRUEBAS LOCALES) ---")
    
    # 1. Simular contacto ORGÁNICO nuevo (número aleatorio)
    nuevo_numero = "593999999999"
    send_mock_webhook(nuevo_numero, "Hola, me interesa el servicio de enfermería orgánica.", "Daniel Solis (Test)")
    
    time.sleep(2)
    
    # 2. Simular contacto EXISTENTE (puedes cambiar esto por un número real de tu DB)
    # Por ejemplo, Juan Perez o similar que ya esté en tu CRM
    # numero_existente = "593987654321" 
    # send_mock_webhook(numero_existente, "Hola, soy un cliente recurrente.")
    
    print("\nSimulación completada. Revisa el Pipeline y el Inbox en tu navegador.")

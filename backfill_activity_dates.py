import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from CoreApps.crm_marketing.models import CrmContact
from CoreApps.chat.models import ChatMensaje
from django.db.models import Max
from django.utils import timezone

def backfill():
    contacts = CrmContact.objects.all()
    total = contacts.count()
    print(f"Sincronizando {total} contactos...")
    
    updated_count = 0
    for c in contacts:
        # Buscar el mensaje más reciente
        last_msg = ChatMensaje.objects.filter(contacto=c).aggregate(Max('fecha_mensaje'))['fecha_mensaje__max']
        
        if last_msg:
            c.fecha_ultima_actividad = last_msg
        else:
            c.fecha_ultima_actividad = c.fecha_registro
            
        c.save(update_fields=['fecha_ultima_actividad'])
        updated_count += 1
        if updated_count % 50 == 0:
            print(f"Procesados {updated_count}/{total}...")
            
    print(f"Sincronización completa. Se actualizaron {updated_count} contactos.")

if __name__ == "__main__":
    backfill()

import os
import sys
import django

# Añadir el directorio actual al path
sys.path.append(os.getcwd())

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from CoreApps.crm_marketing.models import CrmContact
from CoreApps.chat.models import ChatMensaje
from django.db import transaction, models

def cleanup_duplicates():
    # 1. Agrupar por número normalizado
    contacts = list(CrmContact.objects.all())
    groups = {}
    
    for c in contacts:
        if not c.telefono: continue
        tel_limpio = c.telefono.replace('+', '').strip()
        if not tel_limpio: continue
        
        if tel_limpio not in groups:
            groups[tel_limpio] = []
        groups[tel_limpio].append(c)
    
    for tel_limpio, members in groups.items():
        if len(members) > 1:
            members.sort(key=lambda x: x.id) # El más antiguo es el principal
            main = members[0]
            others = members[1:]
            
            with transaction.atomic():
                for other in others:
                    # Mover mensajes
                    ChatMensaje.objects.filter(contacto=other).update(contacto=main)
                    # Mantener whatsapp_jid si el principal no lo tiene
                    if not main.whatsapp_jid and other.whatsapp_jid:
                        main.whatsapp_jid = other.whatsapp_jid
                    
                    # Asegurar que el principal tenga el formato con + si alguno lo tenía
                    if not main.telefono.startswith('+') and other.telefono.startswith('+'):
                        main.telefono = other.telefono
                    
                    main.save()
                    # Eliminar el duplicado
                    other_id = other.id
                    other.delete()
                    print(f"Fusionado contacto {other_id} -> {main.id} (Tel: {tel_limpio})")

    # 2. Eliminar contactos sin número válido
    invalid = CrmContact.objects.filter(models.Q(telefono='+') | models.Q(telefono=''))
    count = invalid.count()
    if count > 0:
        invalid.delete()
        print(f"Eliminados {count} contactos inválidos (sin número).")

if __name__ == '__main__':
    cleanup_duplicates()

import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from CoreApps.crm_marketing.models import CrmContact
from django.utils import timezone

def debug_contacts():
    contacts = CrmContact.objects.filter(nombres__icontains='Daniel Solis PR')
    print(f"Total encontrados: {contacts.count()}")
    for c in contacts:
        print(f"Nombre: {c.nombres}")
        print(f"Etapa: {c.etapa_comercial}")
        print(f"Fecha Actividad: {c.fecha_ultima_actividad}")
        print(f"Fecha Registro: {c.fecha_registro}")
        print("-" * 20)
    
    print(f"Ahora: {timezone.now()}")

if __name__ == "__main__":
    debug_contacts()

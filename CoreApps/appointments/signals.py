from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import AppointmentReminder
from .services import BookingManager

@receiver(post_save, sender=AppointmentReminder)
def trigger_next_cycle(sender, instance, created, **kwargs):
    """
    Escucha cuando un recordatorio cambia su estado a 'AGENDADO'.
    Si el medicamento es recurrente, genera el siguiente ciclo.
    """
    # Solo actuamos si el estado es AGENDADO
    if instance.estado == 'AGENDADO':
        # Nota: BookingManager.create_next_cycle_reminder ya tiene validaciones 
        # internas para evitar duplicados y verificar si el medicamento es recurrente.
        BookingManager.create_next_cycle_reminder(instance)

from django.db import models

class Ciudad(models.Model):
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre de la Ciudad")
    activa = models.BooleanField(default=True, verbose_name="Ciudad Activa")

    class Meta:
        verbose_name = "Ciudad"
        verbose_name_plural = "Ciudades"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

from django.db import models
from core.models import TimeStampedModel

class Categoria(TimeStampedModel):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    def __str__(self): return self.nombre

class Servicio(TimeStampedModel):
    TIPO = (("TOUR","TOUR"),("ALOJAMIENTO","ALOJAMIENTO"),("TRANSPORTE","TRANSPORTE"),("ACTIVIDAD","ACTIVIDAD"))
    tipo = models.CharField(max_length=20, choices=TIPO)
    titulo = models.CharField(max_length=120)
    descripcion = models.TextField(blank=True, null=True)
    duracion_min = models.PositiveSmallIntegerField()
    costo = models.DecimalField(max_digits=12, decimal_places=2)
    capacidad_max = models.PositiveSmallIntegerField()
    punto_encuentro = models.CharField(max_length=255)
    visible_publico = models.BooleanField(default=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.RESTRICT, related_name="servicios")
    class Meta:
        indexes = [models.Index(fields=["categoria"]), models.Index(fields=["tipo"])]
    def __str__(self): return self.titulo

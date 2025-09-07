from django.db import models
from core.models import TimeStampedModel

class Cupon(TimeStampedModel):
    TIPO = (("PORCENTAJE","PORCENTAJE"),("FIJO","FIJO"))
    codigo = models.CharField(max_length=50, unique=True)
    tipo = models.CharField(max_length=12, choices=TIPO)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_inicio = models.DateTimeField(blank=True, null=True)
    fecha_fin = models.DateTimeField(blank=True, null=True)
    estado = models.BooleanField(default=True)
    def __str__(self): return self.codigo

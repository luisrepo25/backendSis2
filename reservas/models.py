from django.db import models
from core.models import TimeStampedModel
from authz.models import Usuario
from catalogo.models import Servicio
from cupones.models import Cupon

class Reserva(TimeStampedModel):
    ESTADO = (("PENDIENTE","PENDIENTE"),("PAGADA","PAGADA"),("CANCELADA","CANCELADA"),("REPROGRAMADA","REPROGRAMADA"))
    usuario = models.ForeignKey(Usuario, on_delete=models.RESTRICT, related_name="reservas")
    fecha_inicio = models.DateTimeField()
    estado = models.CharField(max_length=12, choices=ESTADO, default="PENDIENTE")
    cupon = models.ForeignKey(Cupon, on_delete=models.SET_NULL, null=True, blank=True, related_name="reservas")
    total = models.DecimalField(max_digits=12, decimal_places=2)
    moneda = models.CharField(max_length=3, default="BOB")
    class Meta:
        indexes = [models.Index(fields=["usuario"]), models.Index(fields=["estado"])]

class ReservaServicio(models.Model):
    reserva = models.ForeignKey(Reserva, on_delete=models.CASCADE, related_name="detalles")
    servicio = models.ForeignKey(Servicio, on_delete=models.RESTRICT)
    cantidad = models.PositiveSmallIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    fecha_servicio = models.DateTimeField(blank=True, null=True)
    class Meta:
        unique_together = (("reserva","servicio"),)

class Visitante(TimeStampedModel):
    documento = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    fecha_nacimiento = models.DateField()
    nacionalidad = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(max_length=191, blank=True, null=True)
    telefono = models.CharField(max_length=25, blank=True, null=True)

class ReservaVisitante(models.Model):
    ESTADO = (("CONFIRMADO","CONFIRMADO"),("CANCELADO","CANCELADO"))
    reserva = models.ForeignKey(Reserva, on_delete=models.CASCADE, related_name="visitantes")
    visitante = models.ForeignKey(Visitante, on_delete=models.RESTRICT, related_name="reservas")
    estado = models.CharField(max_length=10, choices=ESTADO, default="CONFIRMADO")
    es_titular = models.BooleanField(default=False)
    # Garantiza un solo titular por reserva:
    class Meta:
        unique_together = (("reserva","visitante"),)
        constraints = [
            models.UniqueConstraint(
                fields=["reserva"],
                condition=models.Q(es_titular=True),
                name="uq_un_titular_por_reserva",
            ),
        ]

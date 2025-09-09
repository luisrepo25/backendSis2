from django.db import models
from core.models import TimeStampedModel
from authz.models import Usuario
from catalogo.models import Servicio
from cupones.models import Cupon
from decimal import Decimal

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
    
    def __str__(self):
        return f"Reserva {self.id} - {self.usuario.nombre} - {self.estado}"
    
    def calcular_total_sin_descuento(self):
        """Calcula el total base sin aplicar cupón"""
        total = Decimal('0')
        for detalle in self.detalles.all():
            total += detalle.precio_unitario * detalle.cantidad
        return total
    
    def aplicar_cupon(self, codigo_cupon):
        """Aplica un cupón a la reserva si es válido"""
        if self.estado != 'PENDIENTE':
            return False, "Solo se pueden aplicar cupones a reservas pendientes"
        
        cupon, mensaje = Cupon.validar_codigo(codigo_cupon)
        if not cupon:
            return False, mensaje
        
        total_base = self.calcular_total_sin_descuento()
        total_con_descuento = cupon.aplicar_descuento(total_base)
        
        self.cupon = cupon
        self.total = total_con_descuento
        self.save()
        
        return True, f"Cupón aplicado. Descuento: {total_base - total_con_descuento}"
    
    def recalcular_total(self):
        """Recalcula el total considerando cupón si existe"""
        total_base = self.calcular_total_sin_descuento()
        
        if self.cupon:
            es_valido, _ = self.cupon.es_valido()
            if es_valido:
                self.total = self.cupon.aplicar_descuento(total_base)
            else:
                # Cupón ya no válido, remover
                self.cupon = None
                self.total = total_base
        else:
            self.total = total_base
        
        self.save()
        return self.total
    
    def puede_cancelar(self):
        """Verifica si la reserva puede ser cancelada"""
        return self.estado in ['PENDIENTE']  # Solo PENDIENTE puede cancelarse
    
    def cancelar(self, razon=None):
        """Cancela la reserva si es posible"""
        if not self.puede_cancelar():
            return False, f"No se puede cancelar una reserva en estado {self.estado}"
        
        self.estado = 'CANCELADA'
        self.save()
        return True, "Reserva cancelada exitosamente"
    
    def confirmar_pago(self):
        """Marca la reserva como pagada"""
        if self.estado != 'PENDIENTE':
            return False, "Solo se pueden confirmar pagos de reservas pendientes"
        
        self.estado = 'PAGADA'
        self.save()
        return True, "Pago confirmado"
    
    def get_visitantes_count(self):
        """Retorna el número total de visitantes"""
        return self.visitantes.filter(estado='CONFIRMADO').count()
    
    def get_servicios_info(self):
        """Retorna información de los servicios incluidos"""
        return [
            {
                'servicio': detalle.servicio.titulo,
                'cantidad': detalle.cantidad,
                'precio_unitario': detalle.precio_unitario,
                'subtotal': detalle.precio_unitario * detalle.cantidad,
                'fecha_servicio': detalle.fecha_servicio
            }
            for detalle in self.detalles.all()
        ]

class ReservaServicio(models.Model):
    reserva = models.ForeignKey(Reserva, on_delete=models.CASCADE, related_name="detalles")
    servicio = models.ForeignKey(Servicio, on_delete=models.RESTRICT)
    cantidad = models.PositiveSmallIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    fecha_servicio = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        unique_together = (("reserva","servicio"),)
    
    def __str__(self):
        return f"{self.servicio.titulo} x{self.cantidad} - Reserva {self.reserva.id}"
    
    def get_subtotal(self):
        """Calcula el subtotal de este detalle"""
        return self.precio_unitario * self.cantidad

class Visitante(TimeStampedModel):
    documento = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    fecha_nacimiento = models.DateField()
    nacionalidad = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(max_length=191, blank=True, null=True)
    telefono = models.CharField(max_length=25, blank=True, null=True)
    
    def __str__(self):
        return f"{self.nombre} {self.apellido} ({self.documento})"
    
    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}"

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
    
    def __str__(self):
        titular = " (TITULAR)" if self.es_titular else ""
        return f"{self.visitante.nombre_completo} - Reserva {self.reserva.id}{titular}"

from django.db import models
from core.models import TimeStampedModel
from django.utils import timezone
from decimal import Decimal

class Cupon(TimeStampedModel):
    TIPO = (("PORCENTAJE","PORCENTAJE"),("FIJO","FIJO"))
    codigo = models.CharField(max_length=50, unique=True)
    tipo = models.CharField(max_length=12, choices=TIPO)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_inicio = models.DateTimeField(blank=True, null=True)
    fecha_fin = models.DateTimeField(blank=True, null=True)
    estado = models.BooleanField(default=True)
    
    def __str__(self): 
        return self.codigo
    
    def es_valido(self):
        """Verifica si el cupón está activo y dentro del período de vigencia"""
        if not self.estado:
            return False, "Cupón inactivo"
            
        ahora = timezone.now()
        if self.fecha_inicio and self.fecha_inicio > ahora:
            return False, "Cupón aún no válido"
            
        if self.fecha_fin and self.fecha_fin < ahora:
            return False, "Cupón expirado"
            
        return True, "Cupón válido"
    
    def calcular_descuento(self, total):
        """Calcula el descuento aplicable sobre un total"""
        if not self.es_valido()[0]:
            return Decimal('0')
            
        if self.tipo == 'PORCENTAJE':
            return (total * self.valor / 100).quantize(Decimal('0.01'))
        elif self.tipo == 'FIJO':
            return min(self.valor, total)  # No puede ser mayor al total
            
        return Decimal('0')
    
    def aplicar_descuento(self, total):
        """Aplica el descuento y retorna el total final"""
        descuento = self.calcular_descuento(total)
        return total - descuento
    
    @classmethod
    def validar_codigo(cls, codigo):
        """Método de clase para validar un código de cupón"""
        try:
            cupon = cls.objects.get(codigo=codigo)
            es_valido, mensaje = cupon.es_valido()
            return cupon if es_valido else None, mensaje
        except cls.DoesNotExist:
            return None, "Cupón no encontrado"

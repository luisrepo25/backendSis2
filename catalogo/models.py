from django.db import models
from core.models import TimeStampedModel
from django.utils import timezone
from decimal import Decimal

class Categoria(TimeStampedModel):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    
    def __str__(self): 
        return self.nombre
    
    def get_servicios_activos(self):
        """Retorna servicios activos y visibles de esta categoría"""
        return self.servicios.filter(visible_publico=True)
    
    def get_servicios_count(self):
        """Cuenta servicios activos en esta categoría"""
        return self.get_servicios_activos().count()

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
    
    def __str__(self): 
        return self.titulo
    
    def esta_disponible(self, fecha=None, cantidad_personas=1):
        """Verifica si el servicio está disponible en una fecha específica"""
        if not self.visible_publico:
            return False, "Servicio no disponible públicamente"
        
        if cantidad_personas > self.capacidad_max:
            return False, f"Capacidad máxima excedida ({self.capacidad_max})"
        
        if fecha:
            # Convertir a date si es datetime
            if hasattr(fecha, 'date'):
                fecha_servicio = fecha.date()
            else:
                fecha_servicio = fecha
                
            if fecha_servicio < timezone.now().date():
                return False, "No se pueden hacer reservas para fechas pasadas"
        
        return True, "Servicio disponible"
    
    def calcular_precio_total(self, cantidad_personas=1, fecha=None):
        """Calcula el precio total para una cantidad de personas"""
        # Aquí podrías implementar lógica de precios dinámicos
        # Por ejemplo: precios especiales por temporada, descuentos por grupo, etc.
        precio_base = self.costo * cantidad_personas
        return precio_base
    
    def get_reservas_activas(self):
        """Retorna reservas activas para este servicio"""
        from reservas.models import ReservaServicio
        return ReservaServicio.objects.filter(
            servicio=self,
            reserva__estado__in=['PENDIENTE', 'PAGADA']
        )
    
    def get_capacidad_disponible(self, fecha=None):
        """Calcula la capacidad disponible para una fecha específica"""
        # Lógica básica - se puede mejorar con fechas específicas
        reservas_activas = self.get_reservas_activas()
        total_reservado = sum(r.cantidad for r in reservas_activas)
        return max(0, self.capacidad_max - total_reservado)
    
    def get_duracion_formateada(self):
        """Retorna la duración en formato legible"""
        horas = self.duracion_min // 60
        minutos = self.duracion_min % 60
        
        if horas > 0 and minutos > 0:
            return f"{horas}h {minutos}min"
        elif horas > 0:
            return f"{horas}h"
        else:
            return f"{minutos}min"
    
    @property
    def precio_formateado(self):
        """Retorna el precio en formato de moneda"""
        return f"Bs. {self.costo:,.2f}"

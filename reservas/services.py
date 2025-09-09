"""
Servicios de Negocio - Capa de lógica compleja para casos de uso
"""
from django.db import transaction
from decimal import Decimal
from datetime import datetime
from typing import Tuple, List, Dict, Optional
from .models import Reserva, ReservaServicio, Visitante, ReservaVisitante
from catalogo.models import Servicio
from cupones.models import Cupon
from authz.models import Usuario


class ReservaService:
    """Servicio para manejar la lógica compleja de reservas"""
    
    @staticmethod
    @transaction.atomic
    def crear_reserva_completa(
        usuario: Usuario,
        servicios_data: List[Dict],
        visitantes_data: List[Dict],
        fecha_inicio: datetime,
        codigo_cupon: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Reserva]]:
        """
        Crea una reserva completa con servicios y visitantes
        
        Args:
            usuario: Usuario que hace la reserva
            servicios_data: Lista de dict con {servicio_id, cantidad, fecha_servicio}
            visitantes_data: Lista de dict con datos de visitantes
            fecha_inicio: Fecha de inicio de la reserva
            codigo_cupon: Código de cupón opcional
            
        Returns:
            (success, mensaje, reserva)
        """
        try:
            # 1. Validar servicios y disponibilidad
            servicios_validados = []
            total_personas = len(visitantes_data)
            
            for servicio_info in servicios_data:
                servicio = Servicio.objects.get(id=servicio_info['servicio_id'])
                cantidad = servicio_info.get('cantidad', 1)
                
                # Verificar disponibilidad
                disponible, mensaje = servicio.esta_disponible(
                    fecha=servicio_info.get('fecha_servicio'),
                    cantidad_personas=cantidad
                )
                
                if not disponible:
                    return False, f"Servicio '{servicio.titulo}': {mensaje}", None
                
                servicios_validados.append({
                    'servicio': servicio,
                    'cantidad': cantidad,
                    'fecha_servicio': servicio_info.get('fecha_servicio'),
                    'precio_unitario': servicio.costo
                })
            
            # 2. Calcular total base
            total_base = sum(
                s['precio_unitario'] * s['cantidad'] 
                for s in servicios_validados
            )
            
            # 3. Crear reserva
            reserva = Reserva.objects.create(
                usuario=usuario,
                fecha_inicio=fecha_inicio,
                total=total_base,
                estado='PENDIENTE'
            )
            
            # 4. Crear detalles de servicios
            for servicio_info in servicios_validados:
                ReservaServicio.objects.create(
                    reserva=reserva,
                    servicio=servicio_info['servicio'],
                    cantidad=servicio_info['cantidad'],
                    precio_unitario=servicio_info['precio_unitario'],
                    fecha_servicio=servicio_info.get('fecha_servicio')
                )
            
            # 5. Crear o vincular visitantes
            primer_visitante = True
            for visitante_data in visitantes_data:
                # Buscar visitante existente o crear nuevo
                visitante, created = Visitante.objects.get_or_create(
                    documento=visitante_data['documento'],
                    defaults=visitante_data
                )
                
                # Vincular a la reserva
                ReservaVisitante.objects.create(
                    reserva=reserva,
                    visitante=visitante,
                    es_titular=primer_visitante,
                    estado='CONFIRMADO'
                )
                primer_visitante = False
            
            # 6. Aplicar cupón si se proporciona
            if codigo_cupon:
                success, mensaje = reserva.aplicar_cupon(codigo_cupon)
                if not success:
                    # No fallar la reserva por cupón inválido, solo notificar
                    mensaje = f"Reserva creada, pero {mensaje}"
                    return True, mensaje, reserva
            
            return True, "Reserva creada exitosamente", reserva
            
        except Servicio.DoesNotExist:
            return False, "Uno o más servicios no existen", None
        except Exception as e:
            return False, f"Error creando reserva: {str(e)}", None


class DisponibilidadService:
    """Servicio para manejar la disponibilidad de servicios"""
    
    @staticmethod
    def verificar_disponibilidad_multiple(
        servicios_ids: List[int],
        fecha: datetime,
        cantidad_personas: int
    ) -> Dict[int, Dict]:
        """
        Verifica disponibilidad de múltiples servicios
        
        Returns:
            Dict con {servicio_id: {disponible: bool, mensaje: str, capacidad_disponible: int}}
        """
        resultado = {}
        
        for servicio_id in servicios_ids:
            try:
                servicio = Servicio.objects.get(id=servicio_id)
                disponible, mensaje = servicio.esta_disponible(fecha, cantidad_personas)
                capacidad_disponible = servicio.get_capacidad_disponible(fecha)
                
                resultado[servicio_id] = {
                    'disponible': disponible,
                    'mensaje': mensaje,
                    'capacidad_disponible': capacidad_disponible,
                    'servicio_titulo': servicio.titulo
                }
            except Servicio.DoesNotExist:
                resultado[servicio_id] = {
                    'disponible': False,
                    'mensaje': 'Servicio no encontrado',
                    'capacidad_disponible': 0,
                    'servicio_titulo': 'Desconocido'
                }
        
        return resultado


class CotizacionService:
    """Servicio para generar cotizaciones de reservas"""
    
    @staticmethod
    def generar_cotizacion(
        servicios_data: List[Dict],
        codigo_cupon: Optional[str] = None
    ) -> Dict:
        """
        Genera una cotización detallada sin crear la reserva
        
        Args:
            servicios_data: Lista de {servicio_id, cantidad}
            codigo_cupon: Código de cupón opcional
            
        Returns:
            Dict con detalles de la cotización
        """
        cotizacion = {
            'detalles': [],
            'subtotal': Decimal('0'),
            'descuento': Decimal('0'),
            'total': Decimal('0'),
            'cupon_valido': False,
            'cupon_mensaje': '',
            'errores': []
        }
        
        # Calcular subtotal
        for servicio_info in servicios_data:
            try:
                servicio = Servicio.objects.get(id=servicio_info['servicio_id'])
                cantidad = servicio_info.get('cantidad', 1)
                subtotal_servicio = servicio.costo * cantidad
                
                cotizacion['detalles'].append({
                    'servicio_id': servicio.id,
                    'servicio_titulo': servicio.titulo,
                    'precio_unitario': servicio.costo,
                    'cantidad': cantidad,
                    'subtotal': subtotal_servicio
                })
                
                cotizacion['subtotal'] += subtotal_servicio
                
            except Servicio.DoesNotExist:
                cotizacion['errores'].append(f"Servicio {servicio_info['servicio_id']} no encontrado")
        
        # Aplicar cupón si se proporciona
        if codigo_cupon and cotizacion['subtotal'] > 0:
            cupon, mensaje = Cupon.validar_codigo(codigo_cupon)
            if cupon:
                cotizacion['cupon_valido'] = True
                cotizacion['descuento'] = cupon.calcular_descuento(cotizacion['subtotal'])
                cotizacion['cupon_mensaje'] = f"Cupón '{codigo_cupon}' aplicado"
            else:
                cotizacion['cupon_mensaje'] = mensaje
        
        # Calcular total final
        cotizacion['total'] = cotizacion['subtotal'] - cotizacion['descuento']
        
        return cotizacion


class EstadisticasService:
    """Servicio para generar estadísticas y reportes"""
    
    @staticmethod
    def obtener_estadisticas_usuario(usuario: Usuario) -> Dict:
        """Obtiene estadísticas de un usuario específico"""
        reservas = Reserva.objects.filter(usuario=usuario)
        
        return {
            'total_reservas': reservas.count(),
            'reservas_pendientes': reservas.filter(estado='PENDIENTE').count(),
            'reservas_pagadas': reservas.filter(estado='PAGADA').count(),
            'reservas_canceladas': reservas.filter(estado='CANCELADA').count(),
            'total_gastado': sum(
                r.total for r in reservas.filter(estado='PAGADA')
            ),
            'servicios_favoritos': ReservaService._obtener_servicios_mas_reservados(usuario)
        }
    
    @staticmethod
    def _obtener_servicios_mas_reservados(usuario: Usuario, limit: int = 5) -> List[Dict]:
        """Obtiene los servicios más reservados por un usuario"""
        # Esta implementación se puede optimizar con anotaciones de Django
        reservas_servicios = ReservaServicio.objects.filter(
            reserva__usuario=usuario,
            reserva__estado__in=['PAGADA', 'PENDIENTE']
        ).select_related('servicio')
        
        servicios_count = {}
        for rs in reservas_servicios:
            servicio_id = rs.servicio.id
            if servicio_id not in servicios_count:
                servicios_count[servicio_id] = {
                    'servicio': rs.servicio.titulo,
                    'count': 0,
                    'total_gastado': Decimal('0')
                }
            servicios_count[servicio_id]['count'] += rs.cantidad
            servicios_count[servicio_id]['total_gastado'] += rs.precio_unitario * rs.cantidad
        
        # Ordenar por cantidad y tomar los primeros 'limit'
        servicios_ordenados = sorted(
            servicios_count.values(),
            key=lambda x: x['count'],
            reverse=True
        )
        
        return servicios_ordenados[:limit]
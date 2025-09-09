from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.db import transaction
from .models import Reserva, Visitante, ReservaVisitante
from .serializers import ReservaSerializer, VisitanteSerializer, ReservaVisitanteSerializer
from .services import ReservaService, DisponibilidadService, CotizacionService, EstadisticasService
from authz.models import Usuario
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers as drf_serializers
from datetime import datetime

class ReservaViewSet(viewsets.ModelViewSet):
    queryset = Reserva.objects.all().select_related("usuario","cupon").prefetch_related("detalles")
    serializer_class = ReservaSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filtrar reservas según el usuario autenticado"""
        qs = super().get_queryset()
        
        # Si el usuario tiene un Usuario asociado en authz
        try:
            usuario = Usuario.objects.get(email=self.request.user.email)
            # Si es admin, puede ver todas las reservas
            if usuario.roles.filter(nombre="ADMIN").exists():
                return qs
            # Si no, solo sus propias reservas
            return qs.filter(usuario=usuario)
        except Usuario.DoesNotExist:
            # Si no hay usuario asociado, no mostrar reservas
            return qs.none()

    @extend_schema(
        summary="Aplicar cupón a reserva",
        request=inline_serializer(
            name="AplicarCuponRequest",
            fields={"codigo_cupon": drf_serializers.CharField()}
        ),
        responses={200: ReservaSerializer}
    )
    @action(detail=True, methods=['post'], url_path='aplicar-cupon')
    def aplicar_cupon(self, request, pk=None):
        """Aplica un cupón a una reserva pendiente"""
        reserva = self.get_object()
        codigo_cupon = request.data.get('codigo_cupon')
        
        if not codigo_cupon:
            return Response({'error': 'Código de cupón requerido'}, status=status.HTTP_400_BAD_REQUEST)
        
        success, mensaje = reserva.aplicar_cupon(codigo_cupon)
        
        if success:
            return Response({
                'mensaje': mensaje,
                'reserva': ReservaSerializer(reserva).data
            }, status=status.HTTP_200_OK)
        else:
            return Response({'error': mensaje}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Cancelar reserva",
        request=inline_serializer(
            name="CancelarReservaRequest", 
            fields={"razon": drf_serializers.CharField(required=False)}
        ),
        responses={200: ReservaSerializer}
    )
    @action(detail=True, methods=['post'], url_path='cancelar')
    def cancelar_reserva(self, request, pk=None):
        """Cancela una reserva si es posible"""
        reserva = self.get_object()
        razon = request.data.get('razon', '')
        
        success, mensaje = reserva.cancelar(razon)
        
        if success:
            return Response({
                'mensaje': mensaje,
                'reserva': ReservaSerializer(reserva).data
            }, status=status.HTTP_200_OK)
        else:
            return Response({'error': mensaje}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Confirmar pago de reserva",
        responses={200: ReservaSerializer}
    )
    @action(detail=True, methods=['post'], url_path='confirmar-pago')
    def confirmar_pago(self, request, pk=None):
        """Confirma el pago de una reserva"""
        reserva = self.get_object()
        
        success, mensaje = reserva.confirmar_pago()
        
        if success:
            return Response({
                'mensaje': mensaje,
                'reserva': ReservaSerializer(reserva).data
            }, status=status.HTTP_200_OK)
        else:
            return Response({'error': mensaje}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Recalcular total de reserva",
        responses={200: ReservaSerializer}
    )
    @action(detail=True, methods=['post'], url_path='recalcular-total')
    def recalcular_total(self, request, pk=None):
        """Recalcula el total de la reserva"""
        reserva = self.get_object()
        nuevo_total = reserva.recalcular_total()
        
        return Response({
            'mensaje': 'Total recalculado',
            'nuevo_total': nuevo_total,
            'reserva': ReservaSerializer(reserva).data
        }, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Obtener mis reservas",
        responses={200: ReservaSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='mis-reservas')
    def mis_reservas(self, request):
        """Retorna las reservas del usuario autenticado"""
        try:
            usuario = Usuario.objects.get(email=request.user.email)
            reservas = Reserva.objects.filter(usuario=usuario).select_related("cupon").prefetch_related("detalles", "visitantes")
            
            # Filtros opcionales
            estado = request.query_params.get('estado')
            if estado:
                reservas = reservas.filter(estado=estado)
                
            serializer = ReservaSerializer(reservas, many=True)
            return Response(serializer.data)
        except Usuario.DoesNotExist:
            return Response({'error': 'Usuario no encontrado'}, status=status.HTTP_404_NOT_FOUND)

    @extend_schema(
        summary="Crear reserva completa",
        request=inline_serializer(
            name="CrearReservaCompletaRequest",
            fields={
                "servicios": drf_serializers.ListField(
                    child=drf_serializers.DictField()
                ),
                "visitantes": drf_serializers.ListField(
                    child=drf_serializers.DictField()
                ),
                "fecha_inicio": drf_serializers.DateTimeField(),
                "codigo_cupon": drf_serializers.CharField(required=False)
            }
        ),
        responses={201: ReservaSerializer}
    )
    @action(detail=False, methods=['post'], url_path='crear-completa')
    def crear_reserva_completa(self, request):
        """Crea una reserva completa con servicios y visitantes"""
        try:
            usuario = Usuario.objects.get(email=request.user.email)
            
            servicios_data = request.data.get('servicios', [])
            visitantes_data = request.data.get('visitantes', [])
            fecha_inicio = request.data.get('fecha_inicio')
            codigo_cupon = request.data.get('codigo_cupon')
            
            if not servicios_data or not visitantes_data or not fecha_inicio:
                return Response({
                    'error': 'servicios, visitantes y fecha_inicio son requeridos'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Convertir fecha_inicio a datetime si es string
            if isinstance(fecha_inicio, str):
                fecha_inicio = datetime.fromisoformat(fecha_inicio.replace('Z', '+00:00'))
            
            success, mensaje, reserva = ReservaService.crear_reserva_completa(
                usuario=usuario,
                servicios_data=servicios_data,
                visitantes_data=visitantes_data,
                fecha_inicio=fecha_inicio,
                codigo_cupon=codigo_cupon
            )
            
            if success:
                return Response({
                    'mensaje': mensaje,
                    'reserva': ReservaSerializer(reserva).data
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({'error': mensaje}, status=status.HTTP_400_BAD_REQUEST)
                
        except Usuario.DoesNotExist:
            return Response({'error': 'Usuario no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class VisitanteViewSet(viewsets.ModelViewSet):
    queryset = Visitante.objects.all()
    serializer_class = VisitanteSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Buscar visitante por documento",
        responses={200: VisitanteSerializer}
    )
    @action(detail=False, methods=['get'], url_path='buscar-por-documento')
    def buscar_por_documento(self, request):
        """Busca un visitante por su documento"""
        documento = request.query_params.get('documento')
        
        if not documento:
            return Response({'error': 'Documento requerido'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            visitante = Visitante.objects.get(documento=documento)
            return Response(VisitanteSerializer(visitante).data)
        except Visitante.DoesNotExist:
            return Response({'error': 'Visitante no encontrado'}, status=status.HTTP_404_NOT_FOUND)

class ReservaVisitanteViewSet(viewsets.ModelViewSet):
    queryset = ReservaVisitante.objects.all()
    serializer_class = ReservaVisitanteSerializer
    permission_classes = [permissions.IsAuthenticated]


# Endpoints adicionales para servicios de negocio

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@extend_schema(
    summary="Verificar disponibilidad de servicios",
    request=inline_serializer(
        name="VerificarDisponibilidadRequest",
        fields={
            "servicios_ids": drf_serializers.ListField(child=drf_serializers.IntegerField()),
            "fecha": drf_serializers.DateTimeField(),
            "cantidad_personas": drf_serializers.IntegerField()
        }
    )
)
def verificar_disponibilidad(request):
    """Verifica la disponibilidad de múltiples servicios"""
    servicios_ids = request.data.get('servicios_ids', [])
    fecha = request.data.get('fecha')
    cantidad_personas = request.data.get('cantidad_personas', 1)
    
    if not servicios_ids or not fecha:
        return Response({
            'error': 'servicios_ids y fecha son requeridos'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Convertir fecha si es string
    if isinstance(fecha, str):
        fecha = datetime.fromisoformat(fecha.replace('Z', '+00:00'))
    
    disponibilidad = DisponibilidadService.verificar_disponibilidad_multiple(
        servicios_ids, fecha, cantidad_personas
    )
    
    return Response(disponibilidad)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@extend_schema(
    summary="Generar cotización de reserva",
    request=inline_serializer(
        name="GenerarCotizacionRequest",
        fields={
            "servicios": drf_serializers.ListField(child=drf_serializers.DictField()),
            "codigo_cupon": drf_serializers.CharField(required=False)
        }
    )
)
def generar_cotizacion(request):
    """Genera una cotización detallada sin crear la reserva"""
    servicios_data = request.data.get('servicios', [])
    codigo_cupon = request.data.get('codigo_cupon')
    
    if not servicios_data:
        return Response({
            'error': 'servicios es requerido'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    cotizacion = CotizacionService.generar_cotizacion(servicios_data, codigo_cupon)
    return Response(cotizacion)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
@extend_schema(
    summary="Obtener estadísticas del usuario",
    responses={200: inline_serializer(
        name="EstadisticasUsuarioResponse",
        fields={
            "total_reservas": drf_serializers.IntegerField(),
            "reservas_pendientes": drf_serializers.IntegerField(),
            "reservas_pagadas": drf_serializers.IntegerField(),
            "reservas_canceladas": drf_serializers.IntegerField(),
            "total_gastado": drf_serializers.DecimalField(max_digits=12, decimal_places=2),
            "servicios_favoritos": drf_serializers.ListField()
        }
    )}
)
def mis_estadisticas(request):
    """Obtiene estadísticas del usuario autenticado"""
    try:
        usuario = Usuario.objects.get(email=request.user.email)
        estadisticas = EstadisticasService.obtener_estadisticas_usuario(usuario)
        return Response(estadisticas)
    except Usuario.DoesNotExist:
        return Response({'error': 'Usuario no encontrado'}, status=status.HTTP_404_NOT_FOUND)
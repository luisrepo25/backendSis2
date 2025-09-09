from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from decimal import Decimal
from .models import Cupon
from .serializers import CuponSerializer, CuponValidacionSerializer
from drf_spectacular.utils import extend_schema

class CuponViewSet(viewsets.ModelViewSet):
    queryset = Cupon.objects.all()
    serializer_class = CuponSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filtrar cupones según el rol del usuario"""
        # Solo admin puede ver todos los cupones
        # TODO: Implementar lógica de roles cuando esté disponible
        return super().get_queryset()

    @extend_schema(
        summary="Validar cupón",
        description="Valida si un cupón es aplicable y calcula el descuento",
        request=CuponValidacionSerializer,
        responses={
            200: CuponSerializer,
            400: "Cupón inválido o expirado",
            404: "Cupón no encontrado"
        }
    )
    @action(detail=False, methods=['post'], url_path='validar')
    def validar_cupon(self, request):
        """Valida un cupón y retorna información de descuento"""
        serializer = CuponValidacionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        codigo = serializer.validated_data['codigo']
        total_reserva = serializer.validated_data.get('total_reserva', Decimal('0'))
        
        try:
            cupon = Cupon.objects.get(codigo=codigo)
        except Cupon.DoesNotExist:
            return Response({'error': 'Cupón no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        
        # Validar si el cupón está activo
        if not cupon.estado:
            return Response({'error': 'Cupón inactivo'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validar fechas de vigencia
        ahora = timezone.now()
        if cupon.fecha_inicio and cupon.fecha_inicio > ahora:
            return Response({'error': 'Cupón aún no válido'}, status=status.HTTP_400_BAD_REQUEST)
            
        if cupon.fecha_fin and cupon.fecha_fin < ahora:
            return Response({'error': 'Cupón expirado'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Calcular descuento
        descuento = self._calcular_descuento(cupon, total_reserva)
        
        # Retornar información del cupón con descuento calculado
        data = CuponSerializer(cupon).data
        data['descuento_aplicable'] = descuento
        data['total_con_descuento'] = total_reserva - descuento
        
        return Response(data, status=status.HTTP_200_OK)
    
    def _calcular_descuento(self, cupon, total):
        """Calcula el descuento basado en el tipo de cupón"""
        if cupon.tipo == 'PORCENTAJE':
            return (total * cupon.valor / 100).quantize(Decimal('0.01'))
        elif cupon.tipo == 'FIJO':
            return min(cupon.valor, total)  # No puede ser mayor al total
        return Decimal('0')

from rest_framework import serializers
from .models import Cupon

class CuponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cupon
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

    def validate(self, data):
        """Validaciones de negocio para cupones"""
        fecha_inicio = data.get('fecha_inicio')
        fecha_fin = data.get('fecha_fin')
        
        if fecha_inicio and fecha_fin and fecha_inicio >= fecha_fin:
            raise serializers.ValidationError("La fecha de inicio debe ser anterior a la fecha de fin")
            
        valor = data.get('valor')
        tipo = data.get('tipo')
        
        if valor is not None and valor <= 0:
            raise serializers.ValidationError("El valor debe ser mayor a 0")
            
        if tipo == 'PORCENTAJE' and valor > 100:
            raise serializers.ValidationError("El porcentaje no puede ser mayor a 100")
            
        return data

class CuponValidacionSerializer(serializers.Serializer):
    """Serializer para validar un cupón antes de aplicarlo"""
    codigo = serializers.CharField(max_length=50)
    total_reserva = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
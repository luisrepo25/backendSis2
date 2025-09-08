from rest_framework import serializers
from .models import Reserva, ReservaServicio, Visitante, ReservaVisitante

class ReservaServicioSerializer(serializers.ModelSerializer):
    class Meta: model = ReservaServicio; fields = ["servicio","cantidad","precio_unitario","fecha_servicio"]

class ReservaSerializer(serializers.ModelSerializer):
    detalles = ReservaServicioSerializer(many=True)
    class Meta:
        model = Reserva
        fields = ["id","usuario","fecha_inicio","estado","cupon","total","moneda","detalles","created_at","updated_at"]
        read_only_fields = ["estado"]

    def create(self, validated_data):
        detalles = validated_data.pop("detalles", [])
        reserva = Reserva.objects.create(**validated_data)
        for d in detalles:
            ReservaServicio.objects.create(reserva=reserva, **d)
        return reserva

class VisitanteSerializer(serializers.ModelSerializer):
    class Meta: model = Visitante; fields = "__all__"

class ReservaVisitanteSerializer(serializers.ModelSerializer):
    class Meta: model = ReservaVisitante; fields = ["reserva","visitante","estado","es_titular"]
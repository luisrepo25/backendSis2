# packages/reservas_pagos/api/serializers.py
from rest_framework import serializers
from bookings.models import Booking
from core.models import Tour, Departure

# Mapeo de estados (DB → presentación en español)
ESTADOS_ES = {
    "pending":   "pendiente",
    "paid":      "pagada",
    "confirmed": "confirmada",
    "completed": "realizada",
    "canceled":  "cancelada",
    "refunded":  "reembolsada",
}

class BookingSerializer(serializers.ModelSerializer):
    # Campos de entrada/salida en español (mapeados a los del modelo con source=)
    usuario = serializers.PrimaryKeyRelatedField(read_only=True, source="user")

    # Claves foráneas (puedes enviar el ID)
    tour = serializers.PrimaryKeyRelatedField(queryset=Tour.objects.all())
    salida = serializers.PrimaryKeyRelatedField(queryset=Departure.objects.all(), source="departure")

    # Campos numéricos y de texto renombrados
    personas = serializers.IntegerField(source="people")
    importe_centavos = serializers.IntegerField(source="amount_cents")
    moneda = serializers.CharField(source="currency")

    # IDs de proveedor de pago (solo lectura, los setea el sistema)
    sesion_checkout_id = serializers.CharField(source="checkout_session_id", read_only=True)
    intento_pago_id = serializers.CharField(source="payment_intent_id", read_only=True)

    # Lectura/representación
    estado = serializers.SerializerMethodField(read_only=True)
    creado_en = serializers.DateTimeField(source="created_at", read_only=True)

    # “Bonitos”
    nombre_tour = serializers.CharField(source="tour.name", read_only=True)
    nombre_salida = serializers.CharField(source="departure.name", read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id",
            "usuario",
            "tour",
            "salida",
            "personas",
            "importe_centavos",
            "moneda",
            "sesion_checkout_id",
            "intento_pago_id",
            "estado",
            "creado_en",
            "nombre_tour",
            "nombre_salida",
        ]
        read_only_fields = [
            "id",
            "usuario",
            "sesion_checkout_id",
            "intento_pago_id",
            "estado",
            "creado_en",
        ]

    def get_estado(self, obj):
        return ESTADOS_ES.get(obj.status, obj.status)

    # Validaciones en español
    def validate_personas(self, v):
        if v <= 0:
            raise serializers.ValidationError("El número de personas debe ser mayor que 0.")
        return v

    def validate_importe_centavos(self, v):
        if v <= 0:
            raise serializers.ValidationError("El importe (en centavos) debe ser mayor que 0.")
        return v

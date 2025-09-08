from rest_framework import serializers
from .models import Categoria, Servicio

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = "__all__"  # expone todos los campos del modelo

class ServicioSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(
        source="categoria.nombre", read_only=True
    )

    class Meta:
        model = Servicio
        fields = "__all__"

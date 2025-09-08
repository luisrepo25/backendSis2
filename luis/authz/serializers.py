# serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from .models import Usuario, Rol, RolUsuario

class RolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = ["id","nombre","created_at","updated_at"]

class UsuarioSerializer(serializers.ModelSerializer):
    roles = serializers.PrimaryKeyRelatedField(queryset=Rol.objects.all(), many=True, required=False)
    class Meta:
        model = Usuario
        fields = ["id","nombre","email","telefono","estado","roles","created_at","updated_at"]

class UsuarioCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ["nombre","email","password_hash","telefono"]

class UsuarioRegistroSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = Usuario
        fields = ["nombre", "email", "password", "password_confirm", "telefono"]
    
    def validate_email(self, value):
        """Validar que el email no esté ya registrado"""
        User = get_user_model()
        if Usuario.objects.filter(email=value).exists() or User.objects.filter(email=value).exists():
            raise serializers.ValidationError("email ya existe")
        return value
    
    def validate(self, attrs):
        """Validar que las contraseñas coincidan"""
        if attrs.get('password') != attrs.get('password_confirm'):
            raise serializers.ValidationError("Las contraseñas no coinciden.")
        return attrs
    
    def create(self, validated_data):
        """Crear usuario con contraseña hasheada"""
        # Remover password_confirm del diccionario
        validated_data.pop('password_confirm')
        
        # Hashear la contraseña para el modelo authz.Usuario (almacenamos un hash fuerte)
        password = validated_data.pop('password')
        validated_data['password_hash'] = make_password(password)

        # Crear Django User nativo (username = email)
        User = get_user_model()
        django_user = User.objects.create_user(
            username=validated_data["email"],
            email=validated_data["email"],
            password=password,
            first_name=validated_data.get("nombre", ""),
        )

        # Crear el usuario de dominio (authz.Usuario)
        usuario = Usuario.objects.create(**validated_data)

        # Adjuntar para uso en la vista
        self._django_user = django_user

        return usuario
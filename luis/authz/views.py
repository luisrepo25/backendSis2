from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db import transaction
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Usuario, Rol
from .serializers import UsuarioSerializer, UsuarioCreateSerializer, RolSerializer, UsuarioRegistroSerializer
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample, inline_serializer
from rest_framework import serializers as drf_serializers
from rest_framework.decorators import action

class RolViewSet(viewsets.ModelViewSet):
    queryset = Rol.objects.all()
    serializer_class = RolSerializer
    permission_classes = [permissions.IsAuthenticated]

class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        return UsuarioCreateSerializer if self.action in ["create"] else UsuarioSerializer

    @extend_schema(
        summary="Asignar rol a usuario",
        request=inline_serializer(
            name="AsignarRolRequest",
            fields={"rol": drf_serializers.CharField()},
        ),
        responses={200: UsuarioSerializer},
    )
    @action(detail=True, methods=["post"], url_path="asignar-rol")
    def asignar_rol(self, request, pk=None):
        usuario = self.get_object()
        nombre_rol = request.data.get("rol")
        if not nombre_rol:
            return Response({"detail": "Falta 'rol'"}, status=400)
        rol, _ = Rol.objects.get_or_create(nombre=nombre_rol)
        usuario.roles.add(rol)
        return Response(UsuarioSerializer(usuario).data)

    @extend_schema(
        summary="Quitar rol a usuario",
        request=inline_serializer(
            name="QuitarRolRequest",
            fields={"rol": drf_serializers.CharField()},
        ),
        responses={200: UsuarioSerializer},
    )
    @action(detail=True, methods=["post"], url_path="quitar-rol")
    def quitar_rol(self, request, pk=None):
        usuario = self.get_object()
        nombre_rol = request.data.get("rol")
        if not nombre_rol:
            return Response({"detail": "Falta 'rol'"}, status=400)
        try:
            rol = Rol.objects.get(nombre=nombre_rol)
        except Rol.DoesNotExist:
            return Response({"detail": "Rol no existe"}, status=404)
        usuario.roles.remove(rol)
        return Response(UsuarioSerializer(usuario).data)

@api_view(['POST'])
@permission_classes([AllowAny])
@extend_schema(
    summary="Registro de nuevo usuario",
    description="Registro de nuevo usuario con asignación de rol CLIENTE y emisión de tokens JWT.",
    request=UsuarioRegistroSerializer,
    responses={
        201: inline_serializer(
            name="RegistroResponse",
            fields={
                "access": drf_serializers.CharField(),
                "refresh": drf_serializers.CharField(),
                "usuario_id": drf_serializers.IntegerField(),
            },
        ),
        400: OpenApiResponse(description="email ya existe / validación fallida"),
    },
    examples=[
        OpenApiExample(
            "Ejemplo de registro",
            value={
                "nombre": "Ana Gomez",
                "email": "ana@example.com",
                "password": "SecretPass123",
                "password_confirm": "SecretPass123",
                "telefono": "71111111"
            },
            request_only=True,
        )
    ],
)
def registrar_usuario(request):
    """Registro de nuevo usuario con asignación de rol CLIENTE y emisión de tokens JWT."""
    serializer = UsuarioRegistroSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        usuario = serializer.save()

        # Asegurar rol CLIENTE
        rol, _ = Rol.objects.get_or_create(nombre="CLIENTE")
        usuario.roles.add(rol)

        # Emitir tokens para el Django User creado
        django_user = getattr(serializer, "_django_user", None)
        if django_user is None:
            # fallback: emitir para authz.Usuario como en login_view
            refresh = RefreshToken.for_user(usuario)
            refresh["uid"] = usuario.id
        else:
            refresh = RefreshToken.for_user(django_user)

    return Response({
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "usuario_id": usuario.id,
    }, status=status.HTTP_201_CREATED)
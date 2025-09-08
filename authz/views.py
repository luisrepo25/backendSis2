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
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string
from django.urls import reverse
import datetime
from django.utils import timezone

# Modelo simple para almacenar tokens de recuperación (puedes migrar a un modelo real si lo deseas)
from django.core.cache import cache

# Endpoint para solicitar recuperación de contraseña
@api_view(["POST"])
@permission_classes([AllowAny])
@extend_schema(
    summary="Solicitar recuperación de contraseña",
    description="Envía un email con un enlace para restablecer la contraseña.",
    request=inline_serializer(
        name="RecuperarPasswordRequest",
        fields={"email": drf_serializers.EmailField()},
    ),
    responses={200: OpenApiResponse(description="Email enviado si existe el usuario")},
)
def solicitar_recuperacion_password(request):
    email = request.data.get("email")
    if not email:
        return Response({"detail": "Falta email"}, status=400)
    try:
        usuario = Usuario.objects.get(email=email)
    except Usuario.DoesNotExist:
        # No revelar si existe o no
        return Response({"detail": "Si el email existe, se enviará un enlace de recuperación."}, status=200)
    # Generar token único y guardar en cache (puedes usar modelo real si prefieres)
    token = get_random_string(48)
    cache.set(f"resetpw:{token}", usuario.id, timeout=60*60)  # 1 hora
    # Construir enlace
    reset_url = request.build_absolute_uri(reverse("reset_password") + f"?token={token}")
    # Enviar email
    send_mail(
        subject="Recuperación de contraseña",
        message=f"Hola {usuario.nombre},\n\nPara restablecer tu contraseña haz clic en el siguiente enlace:\n{reset_url}\n\nSi no solicitaste este cambio, ignora este mensaje.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[usuario.email],
        fail_silently=False,
    )
    return Response({"detail": "Si el email existe, se enviará un enlace de recuperación."}, status=200)

# Endpoint para restablecer contraseña
@api_view(["POST"])
@permission_classes([AllowAny])
@extend_schema(
    summary="Restablecer contraseña",
    description="Permite establecer una nueva contraseña usando el token enviado por email.",
    request=inline_serializer(
        name="ResetPasswordRequest",
        fields={
            "token": drf_serializers.CharField(),
            "password": drf_serializers.CharField(min_length=8),
            "password_confirm": drf_serializers.CharField(min_length=8),
        },
    ),
    responses={200: OpenApiResponse(description="Contraseña restablecida")},
)
def resetear_password(request):
    token = request.data.get("token")
    password = request.data.get("password")
    password_confirm = request.data.get("password_confirm")
    if not token or not password or not password_confirm:
        return Response({"detail": "Faltan campos"}, status=400)
    if password != password_confirm:
        return Response({"detail": "Las contraseñas no coinciden"}, status=400)
    usuario_id = cache.get(f"resetpw:{token}")
    if not usuario_id:
        return Response({"detail": "Token inválido o expirado"}, status=400)
    try:
        usuario = Usuario.objects.get(id=usuario_id)
    except Usuario.DoesNotExist:
        return Response({"detail": "Usuario no encontrado"}, status=404)
    # Cambiar contraseña (hash)
    from django.contrib.auth.hashers import make_password
    usuario.password_hash = make_password(password)
    usuario.save()
    # Si existe el usuario nativo de Django, actualizar también
    from django.contrib.auth import get_user_model
    User = get_user_model()
    django_user = User.objects.filter(email=usuario.email).first()
    if django_user:
        django_user.set_password(password)
        django_user.save()
    # Eliminar token
    cache.delete(f"resetpw:{token}")
    return Response({"detail": "Contraseña restablecida correctamente."}, status=200)

class RolViewSet(viewsets.ModelViewSet):
    queryset = Rol.objects.all()
    serializer_class = RolSerializer
    permission_classes = [permissions.IsAuthenticated]

class UsuarioViewSet(viewsets.ModelViewSet):
    @action(detail=False, methods=["post"], url_path="inhabilitar", permission_classes=[permissions.IsAuthenticated])
    def inhabilitar(self, request):
        """Permite al usuario autenticado inhabilitar (borrado lógico) su cuenta."""
        usuario = Usuario.objects.get(email=request.user.email)
        usuario.estado = "INACTIVO"
        usuario.save()
        return Response({"detail": "Cuenta inhabilitada. Si deseas reactivarla, contacta a un administrador."}, status=200)

    @action(detail=True, methods=["post"], url_path="reactivar", permission_classes=[permissions.IsAuthenticated])
    def reactivar(self, request, pk=None):
        """Permite a un usuario con rol ADMIN reactivar una cuenta de usuario inactiva."""
        usuario_admin = Usuario.objects.get(email=request.user.email)
        if not usuario_admin.roles.filter(nombre="ADMIN").exists():
            return Response({"detail": "No tienes permisos para realizar esta acción."}, status=403)
        usuario = self.get_object()
        if usuario.estado != "INACTIVO":
            return Response({"detail": "La cuenta ya está activa."}, status=400)
        usuario.estado = "ACTIVO"
        usuario.save()
        return Response({"detail": "Cuenta reactivada correctamente."}, status=200)
    @action(detail=False, methods=["get", "put", "patch"], url_path="me")
    def me(self, request):
        """Permite al usuario autenticado ver y actualizar sus propios datos."""
        usuario = Usuario.objects.get(email=request.user.email)
        if request.method == "GET":
            return Response(UsuarioSerializer(usuario).data)
        elif request.method in ["PUT", "PATCH"]:
            serializer = UsuarioSerializer(usuario, data=request.data, partial=(request.method=="PATCH"))
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=400)
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
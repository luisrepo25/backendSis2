from django.urls import path
from .jwt_views import login_view, refresh_view, logout_view
from .views import registrar_usuario, solicitar_recuperacion_password, resetear_password

urlpatterns = [
    # Originales
    path("login/", login_view, name="login"),
    path("refresh/", refresh_view, name="refresh"),
    path("logout/", logout_view, name="logout"),
    path("register/", registrar_usuario, name="register"),
    path("solicitar-recuperacion-password/", solicitar_recuperacion_password, name="solicitar_recuperacion_password"),
    path("reset-password/", resetear_password, name="reset_password"),
    # Alias en español
    path("iniciar-sesion/", login_view, name="iniciar_sesion"),
    path("renovar/", refresh_view, name="renovar"),
    path("cerrar-sesion/", logout_view, name="cerrar_sesion"),
    path("registro/", registrar_usuario, name="registro"),
]

from django.urls import path
from .jwt_views import login_view, refresh_view
from .views import registrar_usuario

urlpatterns = [
    # Originales
    path("login/", login_view, name="login"),
    path("refresh/", refresh_view, name="refresh"),
    path("register/", registrar_usuario, name="register"),
    # Alias en español
    path("iniciar-sesion/", login_view, name="iniciar_sesion"),
    path("renovar/", refresh_view, name="renovar"),
    path("registro/", registrar_usuario, name="registro"),
]

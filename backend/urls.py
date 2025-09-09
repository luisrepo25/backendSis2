from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from authz.views import RolViewSet, UsuarioViewSet
from catalogo.views import CategoriaViewSet, ServicioViewSet
from reservas.views import (
    ReservaViewSet, VisitanteViewSet, ReservaVisitanteViewSet,
    verificar_disponibilidad, generar_cotizacion, mis_estadisticas
)
from cupones.views import CuponViewSet

router = DefaultRouter()
router.register(r"roles", RolViewSet)
router.register(r"usuarios", UsuarioViewSet)
router.register(r"categorias", CategoriaViewSet)
router.register(r"servicios", ServicioViewSet)
router.register(r"reservas", ReservaViewSet)
router.register(r"visitantes", VisitanteViewSet)
router.register(r"reserva-visitantes", ReservaVisitanteViewSet)
router.register(r"cupones", CuponViewSet)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema")),
    path("api/", include(router.urls)),
    path("api/auth/", include("authz.auth_urls")),
    # Alias en español (no rompe compatibilidad):
    path("api/autenticacion/", include("authz.auth_urls")),
    # Endpoints adicionales de servicios de negocio
    path("api/disponibilidad/verificar/", verificar_disponibilidad, name="verificar_disponibilidad"),
    path("api/cotizaciones/generar/", generar_cotizacion, name="generar_cotizacion"),
    path("api/usuarios/mis-estadisticas/", mis_estadisticas, name="mis_estadisticas"),
]

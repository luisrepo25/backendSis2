from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .viewsets import BookingViewSet
# (si dejaste tu /health de prueba) -> from .views import health

router = DefaultRouter()
router.register(r"bookings", BookingViewSet, basename="booking")

urlpatterns = [
    # path("health/", health),  # opcional
    path("", include(router.urls)),
]

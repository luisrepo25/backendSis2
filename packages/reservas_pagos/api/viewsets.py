from django.db.models import Q
from rest_framework import permissions
from rest_framework.viewsets import ModelViewSet
from bookings.models import Booking
from .serializers import BookingSerializer

ESTADOS_DB = {"pendiente": "pending", "pagada": "paid", "confirmada": "confirmed",
              "realizada": "completed", "cancelada": "canceled", "reembolsada": "refunded"}

class EsDuenoOAdmin(permissions.BasePermission):
    """
    Permite: Admin ve todo. Usuario solo sus objetos.
    """
    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_staff:
            return True
        return obj.user_id == request.user.id

class BookingViewSet(ModelViewSet):
    """
    Endpoints en /api/booking/bookings/
    - GET   /bookings/          -> listar mis reservas (admin ve todas)
    - POST  /bookings/          -> crear reserva (usuario autenticado)
    - GET   /bookings/{id}/     -> detalle si es dueño o admin
    - PUT/PATCH/DELETE idem
    """
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated, EsDuenoOAdmin]

    def get_queryset(self):
        """
        Filtros (todos opcionales):
        - ?estado=<pendiente|pagada|confirmada|realizada|cancelada|reembolsada>
        - ?tour=<id>
        - ?salida=<id>
        - ?desde=YYYY-MM-DD   (fecha de creación mínima)
        - ?hasta=YYYY-MM-DD   (fecha de creación máxima)
        - ?orden=<recientes|antiguas>  (por defecto: recientes)
        """
        qs = Booking.objects.select_related("tour", "departure").order_by("-created_at")
        u = self.request.user

        # Propiedad
        if not u.is_staff:
            qs = qs.filter(user=u)

        # Parámetros
        p = self.request.query_params

        # estado (en español -> mapeo a DB)
        estado = p.get("estado")
        if estado:
            estado_db = ESTADOS_DB.get(estado.lower())
            if estado_db:
                qs = qs.filter(status=estado_db)

        # tour / salida
        tour_id = p.get("tour")
        if tour_id:
            qs = qs.filter(tour_id=tour_id)

        salida_id = p.get("salida")
        if salida_id:
            qs = qs.filter(departure_id=salida_id)

        # rango por creación
        desde = p.get("desde")
        hasta = p.get("hasta")
        if desde:
            qs = qs.filter(created_at__date__gte=desde)
        if hasta:
            qs = qs.filter(created_at__date__lte=hasta)

        # orden
        orden = p.get("orden", "recientes")
        if orden == "antiguas":
            qs = qs.order_by("created_at")
        else:
            qs = qs.order_by("-created_at")

        return qs

    def perform_create(self, serializer):
        """
        Forzamos el usuario autenticado. El resto viene en español desde el serializer.
        """
        serializer.save(user=self.request.user)

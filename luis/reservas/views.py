from rest_framework import viewsets, permissions
from .models import Reserva, Visitante, ReservaVisitante
from .serializers import ReservaSerializer, VisitanteSerializer, ReservaVisitanteSerializer

class ReservaViewSet(viewsets.ModelViewSet):
    queryset = Reserva.objects.all().select_related("usuario","cupon").prefetch_related("detalles")
    serializer_class = ReservaSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_authenticated:
            # Si enlazas auth de Django, filtra por usuario real. Aquí asumimos mapping.
            return qs
        return qs.none()

class VisitanteViewSet(viewsets.ModelViewSet):
    queryset = Visitante.objects.all()
    serializer_class = VisitanteSerializer
    permission_classes = [permissions.IsAuthenticated]

class ReservaVisitanteViewSet(viewsets.ModelViewSet):
    queryset = ReservaVisitante.objects.all()
    serializer_class = ReservaVisitanteSerializer
    permission_classes = [permissions.IsAuthenticated]
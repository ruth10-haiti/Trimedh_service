from rest_framework import viewsets, permissions
from .models import Chambre, Lit, Hospitalisation
from .serializers import ChambreSerializer, LitSerializer, HospitalisationSerializer
from comptes.permissions import EstDansHopital  # à créer si besoin

class ChambreViewSet(viewsets.ModelViewSet):
    serializer_class = ChambreSerializer
    permission_classes = [permissions.IsAuthenticated, EstDansHopital]

    def get_queryset(self):
        return Chambre.objects.filter(hopital=self.request.user.hopital)

class LitViewSet(viewsets.ModelViewSet):
    serializer_class = LitSerializer
    permission_classes = [permissions.IsAuthenticated, EstDansHopital]

    def get_queryset(self):
        return Lit.objects.filter(chambre__hopital=self.request.user.hopital)

class HospitalisationViewSet(viewsets.ModelViewSet):
    serializer_class = HospitalisationSerializer
    permission_classes = [permissions.IsAuthenticated, EstDansHopital]

    def get_queryset(self):
        return Hospitalisation.objects.filter(hopital=self.request.user.hopital)
from rest_framework import viewsets, permissions
from .models import TypeSalle, SalleMedicale, Equipement, PlanningSalle, AffectationSalle
from .serializers import (
    TypeSalleSerializer, SalleMedicaleSerializer, EquipementSerializer,
    PlanningSalleSerializer, AffectationSalleSerializer
)
from comptes.permissions import EstDansHopital

class TypeSalleViewSet(viewsets.ModelViewSet):
    serializer_class = TypeSalleSerializer
    permission_classes = [permissions.IsAuthenticated, EstDansHopital]
    def get_queryset(self):
        return TypeSalle.objects.filter(hopital=self.request.user.hopital)

class SalleMedicaleViewSet(viewsets.ModelViewSet):
    serializer_class = SalleMedicaleSerializer
    permission_classes = [permissions.IsAuthenticated, EstDansHopital]
    def get_queryset(self):
        return SalleMedicale.objects.filter(hopital=self.request.user.hopital)

class EquipementViewSet(viewsets.ModelViewSet):
    serializer_class = EquipementSerializer
    permission_classes = [permissions.IsAuthenticated, EstDansHopital]
    def get_queryset(self):
        return Equipement.objects.filter(hopital=self.request.user.hopital)

class PlanningSalleViewSet(viewsets.ModelViewSet):
    serializer_class = PlanningSalleSerializer
    permission_classes = [permissions.IsAuthenticated, EstDansHopital]
    def get_queryset(self):
        return PlanningSalle.objects.filter(salle__hopital=self.request.user.hopital)

class AffectationSalleViewSet(viewsets.ModelViewSet):
    serializer_class = AffectationSalleSerializer
    permission_classes = [permissions.IsAuthenticated, EstDansHopital]
    def get_queryset(self):
        return AffectationSalle.objects.filter(salle__hopital=self.request.user.hopital)
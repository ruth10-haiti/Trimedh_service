from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
from .models import (
    Patient, AdressePatient, PersonneAContacter,
    AssurancePatient, AllergiePatient, AntecedentMedical,
    SuiviPatient
)
from .serializers import (
    PatientSerializer, PatientListSerializer,
    AdressePatientSerializer, PersonneAContacterSerializer,
    AssurancePatientSerializer, AllergiePatientSerializer,
    AntecedentMedicalSerializer, SuiviPatientSerializer
)
from comptes.permissions import (
    EstMedecin, EstPersonnel, EstPatient,
    EstDansMemesTenant
)


class PatientViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des patients
    """
    queryset = Patient.objects.all().order_by('-cree_le')  # CORRECTION: Ajouter order_by
    serializer_class = PatientSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['sexe', 'hopital']
    search_fields = ['nom', 'prenom', 'numero_dossier_medical', 'telephone', 'email']
    ordering_fields = ['nom', 'prenom', 'date_naissance', 'cree_le']
    
    def get_permissions(self):
        """
        Permissions personnalisées selon l'action
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthenticated, EstMedecin | EstPersonnel]
        elif self.action == 'retrieve':
            permission_classes = [IsAuthenticated, EstMedecin | EstPersonnel | EstPatient]
        else:  # list
            permission_classes = [IsAuthenticated, EstMedecin | EstPersonnel]
        return [permission() for permission in permission_classes]
    
    def get_serializer_class(self):
        """Utiliser un serializer différent pour la liste"""
        if self.action == 'list':
            return PatientListSerializer
        return super().get_serializer_class()
    
    def get_queryset(self):
        """
        CORRECTION: Filtrer les patients selon les permissions avec vérification Swagger
        """
        # CORRECTION: Vérifier si c'est pour la génération Swagger
        if getattr(self, 'swagger_fake_view', False):
            return Patient.objects.none()
        
        queryset = super().get_queryset()
        user = self.request.user
        
        # CORRECTION: Vérifier si l'utilisateur est authentifié
        if not user.is_authenticated:
            return Patient.objects.none()
        
        # Les patients ne voient que leur propre dossier
        if hasattr(user, 'role') and user.role == 'patient' and hasattr(user, 'patient_lie'):
            return queryset.filter(pk=user.patient_lie.pk)
        
        # CORRECTION: Filtrer par tenant avec hasattr
        if hasattr(user, 'hopital') and user.hopital:
            queryset = queryset.filter(hopital=user.hopital)
        else:
            # Si l'utilisateur n'a pas d'hôpital, ne retourner aucun patient
            # (sauf admin système qui peut tout voir)
            if not (hasattr(user, 'role') and user.role == 'admin-systeme'):
                return Patient.objects.none()
        
        # Recherche par date de naissance
        date_naissance = self.request.query_params.get('date_naissance', None)
        if date_naissance:
            queryset = queryset.filter(date_naissance=date_naissance)
        
        # Recherche par âge minimum
        age_min = self.request.query_params.get('age_min', None)
        if age_min:
            from datetime import date, timedelta
            max_birth_date = date.today() - timedelta(days=int(age_min)*365)
            queryset = queryset.filter(date_naissance__lte=max_birth_date)
        
        # Recherche par âge maximum
        age_max = self.request.query_params.get('age_max', None)
        if age_max:
            from datetime import date, timedelta
            min_birth_date = date.today() - timedelta(days=int(age_max)*365)
            queryset = queryset.filter(date_naissance__gte=min_birth_date)
        
        return queryset
    
    def perform_create(self, serializer):
        """Surcharge pour ajouter automatiquement le tenant"""
        # CORRECTION: Vérifier que l'utilisateur a un hôpital
        if hasattr(self.request.user, 'hopital') and self.request.user.hopital:
            serializer.save(hopital=self.request.user.hopital)
        else:
            serializer.save()
    
    @action(detail=True, methods=['get'])
    def dossier_complet(self, request, pk=None):
        """Récupérer le dossier complet d'un patient"""
        patient = self.get_object()
        
        # Vérifier les permissions
        if (hasattr(request.user, 'role') and request.user.role == 'patient' and 
            hasattr(request.user, 'patient_lie') and 
            request.user.patient_lie != patient):
            return Response(
                {'error': 'Vous n\'avez pas accès à ce dossier'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(patient)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def statistiques(self, request, pk=None):
        """Statistiques du patient"""
        patient = self.get_object()
        
        from django.utils import timezone
        from datetime import timedelta
        from medical.models import Consultation, Ordonnance, ExamenMedical
        
        data = {
            'consultations_total': Consultation.objects.filter(patient=patient).count(),
            'consultations_12_mois': Consultation.objects.filter(
                patient=patient,
                date_consultation__gte=timezone.now() - timedelta(days=365)
            ).count(),
            'ordonnances_total': Ordonnance.objects.filter(patient=patient).count(),
            'examens_total': ExamenMedical.objects.filter(patient=patient).count(),
            'dernier_suivi': None,
            'allergies_count': AllergiePatient.objects.filter(patient=patient).count(),
            'antecedents_count': AntecedentMedical.objects.filter(patient=patient).count(),
        }
        
        dernier_suivi = SuiviPatient.objects.filter(patient=patient).order_by('-date_suivi').first()
        if dernier_suivi:
            data['dernier_suivi'] = SuiviPatientSerializer(dernier_suivi).data
        
        return Response(data)
    
    @action(detail=True, methods=['post'])
    def ajouter_suivi(self, request, pk=None):
        """Ajouter un suivi médical"""
        patient = self.get_object()
        
        # Vérifier que l'utilisateur est autorisé
        if not (hasattr(request.user, 'role') and request.user.role in ['medecin', 'infirmier']):
            return Response(
                {'error': 'Seuls les médecins et infirmiers peuvent ajouter des suivis'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = SuiviPatientSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(patient=patient)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def ajouter_allergie(self, request, pk=None):
        """Ajouter une allergie"""
        patient = self.get_object()
        serializer = AllergiePatientSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(patient=patient)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def ajouter_antecedent(self, request, pk=None):
        """Ajouter un antécédent médical"""
        patient = self.get_object()
        serializer = AntecedentMedicalSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(patient=patient)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdressePatientViewSet(viewsets.ModelViewSet):
    queryset = AdressePatient.objects.all()
    serializer_class = AdressePatientSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['patient', 'pays', 'ville']
    
    def get_queryset(self):
        """CORRECTION: Vérifier Swagger et authentification"""
        if getattr(self, 'swagger_fake_view', False):
            return AdressePatient.objects.none()
        
        queryset = super().get_queryset()
        user = self.request.user
        
        if not user.is_authenticated:
            return AdressePatient.objects.none()
        
        if hasattr(user, 'hopital') and user.hopital:
            queryset = queryset.filter(patient__hopital=user.hopital)
        
        return queryset


class PersonneAContacterViewSet(viewsets.ModelViewSet):
    queryset = PersonneAContacter.objects.all()
    serializer_class = PersonneAContacterSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['patient', 'relation']
    
    def get_queryset(self):
        """CORRECTION: Vérifier Swagger et authentification"""
        if getattr(self, 'swagger_fake_view', False):
            return PersonneAContacter.objects.none()
        
        queryset = super().get_queryset()
        user = self.request.user
        
        if not user.is_authenticated:
            return PersonneAContacter.objects.none()
        
        if hasattr(user, 'hopital') and user.hopital:
            queryset = queryset.filter(patient__hopital=user.hopital)
        
        return queryset


class AssurancePatientViewSet(viewsets.ModelViewSet):
    queryset = AssurancePatient.objects.all()
    serializer_class = AssurancePatientSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['patient', 'nom_assurance']
    
    def get_queryset(self):
        """CORRECTION: Vérifier Swagger et authentification"""
        if getattr(self, 'swagger_fake_view', False):
            return AssurancePatient.objects.none()
        
        queryset = super().get_queryset()
        user = self.request.user
        
        if not user.is_authenticated:
            return AssurancePatient.objects.none()
        
        if hasattr(user, 'hopital') and user.hopital:
            queryset = queryset.filter(patient__hopital=user.hopital)
        
        return queryset


class AllergiePatientViewSet(viewsets.ModelViewSet):
    queryset = AllergiePatient.objects.all()
    serializer_class = AllergiePatientSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['patient', 'gravite']
    
    def get_queryset(self):
        """CORRECTION: Vérifier Swagger et authentification"""
        if getattr(self, 'swagger_fake_view', False):
            return AllergiePatient.objects.none()
        
        queryset = super().get_queryset()
        user = self.request.user
        
        if not user.is_authenticated:
            return AllergiePatient.objects.none()
        
        if hasattr(user, 'hopital') and user.hopital:
            queryset = queryset.filter(patient__hopital=user.hopital)
        
        return queryset


class AntecedentMedicalViewSet(viewsets.ModelViewSet):
    queryset = AntecedentMedical.objects.all()
    serializer_class = AntecedentMedicalSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['patient', 'type_antecedent', 'en_cours']
    
    def get_queryset(self):
        """CORRECTION: Vérifier Swagger et authentification"""
        if getattr(self, 'swagger_fake_view', False):
            return AntecedentMedical.objects.none()
        
        queryset = super().get_queryset()
        user = self.request.user
        
        if not user.is_authenticated:
            return AntecedentMedical.objects.none()
        
        if hasattr(user, 'hopital') and user.hopital:
            queryset = queryset.filter(patient__hopital=user.hopital)
        
        return queryset


class SuiviPatientViewSet(viewsets.ModelViewSet):
    queryset = SuiviPatient.objects.all().order_by('-date_suivi')  # CORRECTION: Ajouter order_by
    serializer_class = SuiviPatientSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['patient', 'medecin', 'date_suivi']
    ordering_fields = ['date_suivi', 'created_at']
    ordering = ['-date_suivi']
    
    def get_queryset(self):
        """CORRECTION: Vérifier Swagger et authentification"""
        if getattr(self, 'swagger_fake_view', False):
            return SuiviPatient.objects.none()
        
        queryset = super().get_queryset()
        user = self.request.user
        
        if not user.is_authenticated:
            return SuiviPatient.objects.none()
        
        if hasattr(user, 'hopital') and user.hopital:
            queryset = queryset.filter(patient__hopital=user.hopital)
        
        return queryset
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update']:
            permission_classes = [IsAuthenticated, EstMedecin | EstPersonnel]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
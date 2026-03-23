from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import authenticate
from django.conf import settings
from .models import Utilisateur
from .serializers import (
    UtilisateurSerializer, InscriptionSerializer,
    LoginSerializer, ChangePasswordSerializer, UpdateProfileSerializer
)
from .permissions import (
    EstAdminSysteme, EstProprietaireHopital, EstMedecin,
    EstPersonnel, EstPatient, PeutModifierUtilisateur
)

class UtilisateurViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des utilisateurs
    """
    queryset = Utilisateur.objects.all()
    serializer_class = UtilisateurSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['role', 'hopital', 'is_active']
    search_fields = ['email', 'nom_complet']
    ordering_fields = ['nom_complet', 'cree_le', 'derniere_connexion']
    
    def get_permissions(self):
        """
        Permissions personnalisées selon l'action
        """
        if self.action == 'create':
            permission_classes = [IsAuthenticated, EstAdminSysteme | EstProprietaireHopital]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthenticated, PeutModifierUtilisateur]
        elif self.action == 'retrieve':
            permission_classes = [IsAuthenticated]
        else:  # list
            permission_classes = [IsAuthenticated, EstAdminSysteme | EstProprietaireHopital]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """
        CORRECTION: Filtrer les utilisateurs selon les permissions
        avec vérification pour Swagger
        """
        # CORRECTION 1: Vérifier si c'est pour la génération Swagger
        if getattr(self, 'swagger_fake_view', False):
            return Utilisateur.objects.none()
        
        user = self.request.user
        
        # CORRECTION 2: Vérifier si l'utilisateur est authentifié
        if not user.is_authenticated:
            return Utilisateur.objects.none()
        
        # Admins système voient tout
        if hasattr(user, 'role') and user.role == 'admin-systeme':
            return Utilisateur.objects.all()
        
        # Propriétaires voient les utilisateurs de leur tenant
        if hasattr(user, 'role') and user.role == 'proprietaire-hopital' and hasattr(user, 'hopital') and user.hopital:
            return Utilisateur.objects.filter(hopital=user.hopital)
        
        # Médecins voient les utilisateurs de leur tenant (sauf patients)
        if hasattr(user, 'role') and user.role == 'medecin' and hasattr(user, 'hopital') and user.hopital:
            return Utilisateur.objects.filter(hopital=user.hopital).exclude(role='patient')
        
        # Personnel voient les utilisateurs de leur tenant (sauf patients)
        if hasattr(user, 'role') and user.role in ['personnel', 'secretaire', 'infirmier'] and hasattr(user, 'hopital') and user.hopital:
            return Utilisateur.objects.filter(hopital=user.hopital).exclude(role='patient')
        
        # Patients ne voient que leur propre profil
        if hasattr(user, 'role') and user.role == 'patient':
            return Utilisateur.objects.filter(pk=user.pk)
        
        return Utilisateur.objects.none()
    
    def perform_create(self, serializer):
        """Surcharge pour enregistrer qui a créé l'utilisateur"""
        serializer.save(modifie_par=self.request.user)
    
    @action(detail=False, methods=['get'])
    def profile(self, request):
        """Récupérer le profil de l'utilisateur connecté"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['put', 'patch'])
    def update_profile(self, request):
        """Mettre à jour le profil de l'utilisateur connecté"""
        serializer = UpdateProfileSerializer(
            request.user,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def change_password(self, request, pk=None):
        """Changer le mot de passe d'un utilisateur"""
        utilisateur = self.get_object()
        
        # Vérifier les permissions
        if utilisateur != request.user and not (
            hasattr(request.user, 'role') and request.user.role in ['admin-systeme', 'proprietaire-hopital']
        ):
            return Response(
                {'error': 'Vous n\'avez pas la permission de modifier ce mot de passe'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            # Vérifier l'ancien mot de passe
            if not utilisateur.check_password(serializer.validated_data['old_password']):
                return Response(
                    {'old_password': 'Mot de passe incorrect'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Mettre à jour le mot de passe
            utilisateur.set_password(serializer.validated_data['new_password'])
            utilisateur.save()
            
            return Response({'message': 'Mot de passe mis à jour avec succès'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Activer/désactiver un utilisateur"""
        utilisateur = self.get_object()
        
        # Vérifier les permissions
        if not (hasattr(request.user, 'role') and request.user.role in ['admin-systeme', 'proprietaire-hopital']):
            return Response(
                {'error': 'Vous n\'avez pas la permission de modifier cet utilisateur'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        utilisateur.is_active = not utilisateur.is_active
        utilisateur.save()
        
        status_msg = 'activé' if utilisateur.is_active else 'désactivé'
        return Response({
            'message': f'Utilisateur {status_msg} avec succès',
            'is_active': utilisateur.is_active
        })

class LoginView(APIView):
    """Vue pour l'authentification"""
    
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        
        if serializer.is_valid():
            utilisateur = serializer.validated_data['utilisateur']
            
            # CORRECTION: Vérifier que l'utilisateur a un ID avant de générer le token
            if not utilisateur.pk:
                # Si l'utilisateur n'a pas d'ID, le sauvegarder
                utilisateur.save()
            
            # Générer les tokens JWT
            try:
                refresh = RefreshToken.for_user(utilisateur)
                
                # Sérialiser les données utilisateur
                user_serializer = UtilisateurSerializer(utilisateur)
                
                return Response({
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'utilisateur': user_serializer.data
                })
            except AttributeError as e:
                # CORRECTION: Gérer l'erreur si le modèle n'a pas le bon champ ID
                return Response(
                    {'error': f'Erreur de configuration du token: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(APIView):
    """Vue pour la déconnexion"""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh_token")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            return Response(
                {'message': 'Déconnexion réussie'},
                status=status.HTTP_205_RESET_CONTENT
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

class InscriptionView(APIView):
    """Vue pour l'inscription (principalement pour les patients)"""
    
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = InscriptionSerializer(data=request.data)
        
        if serializer.is_valid():
            # CORRECTION: Sauvegarder d'abord l'utilisateur pour avoir un ID
            utilisateur = serializer.save()
            
            # CORRECTION: Forcer la sauvegarde pour s'assurer que l'utilisateur a un ID
            if not utilisateur.pk:
                utilisateur.save()
            
            # Générer les tokens JWT
            try:
                refresh = RefreshToken.for_user(utilisateur)
                user_serializer = UtilisateurSerializer(utilisateur)
                
                return Response({
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'utilisateur': user_serializer.data,
                    'message': 'Inscription réussie'
                }, status=status.HTTP_201_CREATED)
            except AttributeError as e:
                # CORRECTION: Gérer l'erreur si le modèle n'a pas le bon champ ID
                return Response(
                    {'error': f'Erreur lors de la création du token: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
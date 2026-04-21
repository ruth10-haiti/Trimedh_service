from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from .tokens import account_activation_token
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse  # Ajouté pour construire l'URL absolue
from .tokens import account_activation_token
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import authenticate
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
        """Permissions personnalisées selon l'action"""
        if self.action == 'create':
            permission_classes = [IsAuthenticated, EstAdminSysteme | EstProprietaireHopital]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthenticated, PeutModifierUtilisateur]
        elif self.action == 'retrieve':
            permission_classes = [IsAuthenticated]
        elif self.action == 'list':
            permission_classes = [IsAuthenticated, EstAdminSysteme | EstProprietaireHopital | EstMedecin]
        return [permission() for permission in permission_classes]
    

    def get_queryset(self):
        """Filtrer les utilisateurs selon les permissions"""
        queryset = super().get_queryset()
        user = self.request.user

        if user.role == 'admin-systeme':
            return queryset

        if user.role == 'proprietaire-hopital' and user.hopital:
            return queryset.filter(hopital=user.hopital)

        if user.role == 'medecin' and user.hopital:
            return queryset.filter(hopital=user.hopital).exclude(role='patient')

        if user.role in ['personnel', 'secretaire', 'infirmier'] and user.hopital:
            return queryset.filter(hopital=user.hopital).exclude(role='patient')

        if user.role == 'patient':
            return queryset.filter(pk=user.pk)

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

        if utilisateur != request.user and not (
            request.user.role in ['admin-systeme', 'proprietaire-hopital']
        ):
            return Response(
                {'error': 'Vous n\'avez pas la permission de modifier ce mot de passe'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            if not utilisateur.check_password(serializer.validated_data['old_password']):
                return Response(
                    {'old_password': 'Mot de passe incorrect'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            utilisateur.set_password(serializer.validated_data['new_password'])
            utilisateur.save()

            return Response({'message': 'Mot de passe mis à jour avec succès'})

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Activer/désactiver un utilisateur"""
        utilisateur = self.get_object()

        if request.user.role not in ['admin-systeme', 'proprietaire-hopital']:
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

            refresh = RefreshToken.for_user(utilisateur)
            user_serializer = UtilisateurSerializer(utilisateur)
            user_data = user_serializer.data

            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': user_data,
                'tenant': user_data.get('hopital_detail')
            })

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
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = InscriptionSerializer(data=request.data)
        if serializer.is_valid():
            utilisateur = serializer.save()
            temp_password = serializer.temp_password

            # Générer le lien de vérification vers l'API (pas vers un frontend externe)
            uid = urlsafe_base64_encode(force_bytes(utilisateur.pk))
            token = account_activation_token.make_token(utilisateur)
            # Construire l'URL absolue vers la vue VerifyEmailView
            verification_link = request.build_absolute_uri(
                reverse('verify-email') + f"?uidb64={uid}&token={token}"
            )

            # Envoyer l'email
            subject = "Activez votre compte TRIMED"
            html_message = render_to_string('emails/verification_email.html', {
                'user': utilisateur,
                'temp_password': temp_password,
                'verification_link': verification_link,
            })
            plain_message = f"Bonjour {utilisateur.nom_complet},\n\nVotre mot de passe temporaire : {temp_password}\n\nActivez votre compte : {verification_link}"

            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [utilisateur.email],
                html_message=html_message,
                fail_silently=False,
            )

            return Response({
                'message': 'Inscription réussie. Vérifiez votre email pour activer votre compte.',
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        uidb64 = request.GET.get('uidb64')
        token = request.GET.get('token')

        if not uidb64 or not token:
            return Response({"error": "Paramètres manquants."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            utilisateur = Utilisateur.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, Utilisateur.DoesNotExist):
            utilisateur = None

        if utilisateur and account_activation_token.check_token(utilisateur, token):
            utilisateur.is_active = True
            utilisateur.save()
            return Response({"message": "Email vérifié avec succès ! Vous pouvez maintenant vous connecter."})
        else:
            return Response({"error": "Lien invalide ou expiré."}, status=status.HTTP_400_BAD_REQUEST)
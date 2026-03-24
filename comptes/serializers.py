# comptes/serializers.py
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.utils import timezone
from django.db import transaction
from .models import Utilisateur

class UtilisateurSerializer(serializers.ModelSerializer):
    hopital_detail = serializers.SerializerMethodField()
    
    def get_hopital_detail(self, obj):
        """Récupérer les détails de l'hôpital sans créer de récursion"""
        if obj.hopital:
            # CORRECTION: Retourner un dictionnaire simple au lieu du TenantSerializer
            # pour éviter la récursion infinie
            return {
                'tenant_id': obj.hopital.tenant_id,
                'nom': obj.hopital.nom,
                'adresse': obj.hopital.adresse,
                'telephone': obj.hopital.telephone,
                'email_professionnel': obj.hopital.email_professionnel,
                'directeur': obj.hopital.directeur,
                'nombre_de_lits': obj.hopital.nombre_de_lits,
                'numero_enregistrement': obj.hopital.numero_enregistrement,
                'statut': obj.hopital.statut,
                'type_abonnement': obj.hopital.type_abonnement,
                'statut_verification_document': obj.hopital.statut_verification_document,
                'cree_le': obj.hopital.cree_le,
            }
        return None
    
    class Meta:
        model = Utilisateur
        fields = [
            'utilisateur_id', 'nom_complet', 'email', 'role',
            'hopital', 'hopital_detail', 'cree_le', 'derniere_connexion',
            'is_active', 'is_staff', 'last_login'
        ]
        read_only_fields = [
            'utilisateur_id', 'cree_le', 'derniere_connexion',
            'last_login', 'is_staff'
        ]
        extra_kwargs = {
            'email': {'required': True},
            'nom_complet': {'required': True},
            'role': {'required': True}
        }
    
    def validate_email(self, value):
        """Validation de l'email"""
        if Utilisateur.objects.filter(email=value).exists():
            raise serializers.ValidationError("Cet email est déjà utilisé")
        return value
    
    def validate_role(self, value):
        """Validation du rôle"""
        roles_autorises = [choice[0] for choice in Utilisateur.Role.choices]
        if value not in roles_autorises:
            raise serializers.ValidationError(f"Rôle invalide. Choix: {roles_autorises}")
        return value


class InscriptionSerializer(serializers.Serializer):
    """
    Serializer personnalisé pour l'inscription qui gère la création
    du Tenant pour les propriétaires d'hôpitaux
    """
    # Champs utilisateur
    nom_complet = serializers.CharField(required=True, min_length=3)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, required=True)
    role = serializers.ChoiceField(choices=Utilisateur.Role.choices, default='patient')
    
    # Champs optionnels pour compatibilité frontend
    nom = serializers.CharField(required=False, allow_blank=True, write_only=True)
    prenom = serializers.CharField(required=False, allow_blank=True, write_only=True)
    is_active = serializers.BooleanField(required=False, default=False, write_only=True)
    
    # Champs tenant (optionnel)
    hopital_data = serializers.DictField(required=False, allow_null=True, write_only=True)
    
    def validate_email(self, value):
        """Vérifier que l'email n'existe pas déjà"""
        if Utilisateur.objects.filter(email=value).exists():
            raise serializers.ValidationError("Cet email est déjà utilisé")
        return value
    
    def validate(self, data):
        """Validation croisée des données"""
        # Vérifier que les mots de passe correspondent
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password': 'Les mots de passe ne correspondent pas'
            })
        
        # Vérifier que hopital_data est présent pour les propriétaires d'hôpitaux
        if data.get('role') == 'proprietaire-hopital':
            if not data.get('hopital_data'):
                raise serializers.ValidationError({
                    'hopital_data': 'Les données de l\'hôpital sont requises pour un propriétaire d\'hôpital'
                })
            
            # Validation des champs requis pour le tenant
            hopital_data = data.get('hopital_data', {})
            if not hopital_data.get('nom'):
                raise serializers.ValidationError({
                    'hopital_data.nom': 'Le nom de l\'hôpital est requis'
                })
        
        return data
    
    @transaction.atomic
    def create(self, validated_data):
        """Création de l'utilisateur et du tenant (si applicable)"""
        # Extraire les données
        hopital_data = validated_data.pop('hopital_data', None)
        validated_data.pop('confirm_password', None)
        validated_data.pop('nom', None)
        validated_data.pop('prenom', None)
        is_active = validated_data.pop('is_active', False)
        password = validated_data.pop('password')
        
        nom_complet = validated_data['nom_complet']
        
        # Créer l'utilisateur
        utilisateur = Utilisateur.objects.creer_utilisateur(
            email=validated_data['email'],
            nom_complet=nom_complet,
            mot_de_passe=password,
            role=validated_data.get('role', 'patient'),
            hopital=None
        )
        
        # Appliquer is_active
        utilisateur.is_active = is_active
        utilisateur.save(update_fields=['is_active'])
        
        # Créer le Tenant pour propriétaire d'hôpital
        if hopital_data and utilisateur.role == 'proprietaire-hopital':
            try:
                from gestion_tenants.models import Tenant
                
                tenant = Tenant.objects.create(
                    nom=hopital_data.get('nom'),
                    adresse=hopital_data.get('adresse', ''),
                    telephone=hopital_data.get('telephone', ''),
                    email_professionnel=hopital_data.get('email_professionnel', ''),
                    directeur=hopital_data.get('directeur', nom_complet),
                    nombre_de_lits=hopital_data.get('nombre_de_lits', 1),
                    numero_enregistrement=hopital_data.get('numero_enregistrement', ''),
                    statut=hopital_data.get('statut', 'actif'),
                    type_abonnement=hopital_data.get('type_abonnement', 'basic'),
                    statut_verification_document=hopital_data.get('statut_verification_document', 'en_attente'),
                    proprietaire_utilisateur=utilisateur,
                    cree_par_utilisateur=utilisateur,
                )
                
                utilisateur.hopital = tenant
                utilisateur.save(update_fields=['hopital'])
                
                # Forcer is_active=False pour les propriétaires
                utilisateur.is_active = False
                utilisateur.save(update_fields=['is_active'])
                
            except Exception as e:
                utilisateur.delete()
                raise serializers.ValidationError({
                    'hopital_data': f'Erreur lors de la création de l\'hôpital: {str(e)}'
                })
        
        return utilisateur


class LoginSerializer(serializers.Serializer):
    # CORRECTION: Accepter email OU username
    username = serializers.CharField()  # Renommer email en username
    password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        username = data.get('username')
        password = data.get('password')
        
        if username and password:
            # CORRECTION: Essayer avec email puis avec username
            utilisateur = None
            if '@' in username:
                utilisateur = authenticate(email=username, password=password)
            if not utilisateur:
                utilisateur = authenticate(username=username, password=password)
            
            if not utilisateur:
                raise serializers.ValidationError("Email ou mot de passe incorrect")
            
            if not utilisateur.is_active:
                raise serializers.ValidationError("Ce compte est désactivé. Veuillez contacter l'administrateur.")
            
            utilisateur.derniere_connexion = timezone.now()
            utilisateur.save(update_fields=['derniere_connexion'])
            
            data['utilisateur'] = utilisateur
        else:
            raise serializers.ValidationError("Email et mot de passe requis")
        
        return data


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    confirm_password = serializers.CharField(required=True)
    
    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password': 'Les nouveaux mots de passe ne correspondent pas'
            })
        return data


class UpdateProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Utilisateur
        fields = ['nom_complet', 'email', 'role', 'hopital']
        read_only_fields = ['email', 'role']
    
    def validate_nom_complet(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Le nom complet doit contenir au moins 3 caractères")
        return value
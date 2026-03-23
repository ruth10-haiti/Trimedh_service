from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.core.validators import EmailValidator

class GestionnaireUtilisateur(BaseUserManager):
    """Gestionnaire personnalisé pour les utilisateurs"""
    
    def creer_utilisateur(self, email, nom_complet, mot_de_passe=None, **extra_fields):
        """Crée un utilisateur normal (méthode en français)"""
        if not email:
            raise ValueError('L\'email est obligatoire')
        
        email = self.normalize_email(email)
        utilisateur = self.model(
            email=email,
            nom_complet=nom_complet,
            **extra_fields
        )
        utilisateur.set_password(mot_de_passe)
        utilisateur.save(using=self._db)
        return utilisateur
    
    def creer_superutilisateur(self, email, nom_complet, mot_de_passe=None, **extra_fields):
        """Crée un superutilisateur (méthode en français)"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin-systeme')
        
        # Vérifications
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Le superutilisateur doit avoir is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Le superutilisateur doit avoir is_superuser=True.')
        
        return self.creer_utilisateur(email, nom_complet, mot_de_passe, **extra_fields)
    
    # Méthodes requises par Django (en anglais)
    def create_user(self, email, nom_complet, password=None, **extra_fields):
        """Alias pour creer_utilisateur (requis par Django)"""
        return self.creer_utilisateur(email, nom_complet, password, **extra_fields)
    
    def create_superuser(self, email, nom_complet, password=None, **extra_fields):
        """Alias pour creer_superutilisateur (requis par Django)"""
        return self.creer_superutilisateur(email, nom_complet, password, **extra_fields)


class Utilisateur(AbstractBaseUser, PermissionsMixin):
    """
    TABLE Utilisateur - Modèle personnalisé
    """
    
    class Role(models.TextChoices):
        ADMIN_SYSTEME = 'admin-systeme', 'Administrateur Système'
        PROPRIETAIRE_HOPITAL = 'proprietaire-hopital', 'Propriétaire Hôpital'
        MEDECIN = 'medecin', 'Médecin'
        INFIRMIER = 'infirmier', 'Infirmier'
        SECRETAIRE = 'secretaire', 'Secrétaire'
        PERSONNEL = 'personnel', 'Personnel'
        PATIENT = 'patient', 'Patient'
    
    # CORRECTION: Ajouter un champ 'id' pour SimpleJWT
    id = models.AutoField(primary_key=True)  # Django standard
    utilisateur_id = models.IntegerField(unique=True, null=True, blank=True)  # Garder pour compatibilité
    
    nom_complet = models.CharField(max_length=255)
    email = models.EmailField(
        max_length=100,
        unique=True,
        validators=[EmailValidator()]
    )
    mot_de_passe = models.CharField(max_length=255, editable=False)
    
    role = models.CharField(
        max_length=50,
        choices=Role.choices,
        default=Role.PATIENT
    )
    
    hopital = models.ForeignKey(
        'gestion_tenants.Tenant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='hopital_id',
        related_name='utilisateurs'
    )
    
    cree_le = models.DateTimeField(default=timezone.now)
    
    # Champs Django requis
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    derniere_connexion = models.DateTimeField(null=True, blank=True)
    
    # Relations spécifiques (pour les signaux)
    derniere_modification = models.DateTimeField(auto_now=True)
    modifie_par = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='utilisateurs_modifies'
    )
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nom_complet']
    
    objects = GestionnaireUtilisateur()
    
    def __str__(self):
        return f"{self.nom_complet} ({self.get_role_display()})"
    
    def save(self, *args, **kwargs):
        # CORRECTION: Assurer que utilisateur_id est égal à id pour compatibilité
        if not self.pk:
            self.cree_le = timezone.now()
        super().save(*args, **kwargs)
        # Après sauvegarde, synchroniser utilisateur_id avec id
        if not self.utilisateur_id:
            self.utilisateur_id = self.id
            super().save(update_fields=['utilisateur_id'])
    
    class Meta:
        db_table = 'utilisateur'
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
            models.Index(fields=['hopital']),
            models.Index(fields=['id']),  # Ajouter index sur id
        ]
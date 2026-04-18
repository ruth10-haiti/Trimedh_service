import uuid
from django.db import models
from django.utils import timezone
from gestion_tenants.models import Tenant
from comptes.models import Utilisateur
from patients.models import Patient

class TypeSalle(models.Model):
    """Catégorie de salle (consultation, chirurgie, réveil, etc.)"""
    nom = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    hopital = models.ForeignKey(Tenant, on_delete=models.CASCADE)

    class Meta:
        db_table = 'type_salle'

    def __str__(self):
        return self.nom


class SalleMedicale(models.Model):
    """Salle médicale (consultation, soins, intervention)"""
    STATUT_CHOICES = [
        ('disponible', 'Disponible'),
        ('occupee', 'Occupée'),
        ('maintenance', 'En maintenance'),
    ]
    salle_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=100)
    type_salle = models.ForeignKey(TypeSalle, on_delete=models.PROTECT)
    hopital = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    capacite = models.IntegerField(default=1)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='disponible')
    duree_consultation_defaut = models.IntegerField(default=30)  # minutes
    prix_par_seance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    est_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'salle_medicale'

    def __str__(self):
        return f"{self.nom} ({self.get_statut_display()})"


class Equipement(models.Model):
    """Matériel médical"""
    nom = models.CharField(max_length=200)
    reference = models.CharField(max_length=100, blank=True)
    hopital = models.ForeignKey(Tenant, on_delete=models.CASCADE)

    class Meta:
        db_table = 'equipement'

    def __str__(self):
        return self.nom


class SalleEquipement(models.Model):
    """Association salle ↔ équipement"""
    salle = models.ForeignKey(SalleMedicale, on_delete=models.CASCADE)
    equipement = models.ForeignKey(Equipement, on_delete=models.CASCADE)
    quantite = models.IntegerField(default=1)

    class Meta:
        db_table = 'salle_equipement'
        unique_together = ('salle', 'equipement')


class PlanningSalle(models.Model):
    """Réservation d'une salle"""
    STATUT_CHOICES = [
        ('reservee', 'Réservée'),
        ('confirmee', 'Confirmée'),
        ('terminee', 'Terminée'),
        ('annulee', 'Annulée'),
    ]
    planning_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    salle = models.ForeignKey(SalleMedicale, on_delete=models.CASCADE)
    medecin = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, limit_choices_to={'role': 'medecin'})
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, null=True, blank=True)
    date = models.DateField()
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()
    motif = models.CharField(max_length=255, blank=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='reservee')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'planning_salle'
        unique_together = ('salle', 'date', 'heure_debut')

    def __str__(self):
        return f"{self.salle.nom} - {self.date} {self.heure_debut}"


class AffectationSalle(models.Model):
    """Assignation permanente d'une salle à un médecin/service"""
    affectation_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    salle = models.ForeignKey(SalleMedicale, on_delete=models.CASCADE)
    medecin = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, null=True, blank=True, limit_choices_to={'role': 'medecin'})
    service = models.CharField(max_length=100, blank=True)
    date_debut = models.DateField()
    date_fin = models.DateField(null=True, blank=True)
    actif = models.BooleanField(default=True)

    class Meta:
        db_table = 'affectation_salle'
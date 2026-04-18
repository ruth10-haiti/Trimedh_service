import uuid
from django.db import models
from gestion_tenants.models import Tenant
from patients.models import Patient

class Chambre(models.Model):
    """Chambre d'hospitalisation"""
    STATUT_CHOICES = [
        ('disponible', 'Disponible'),
        ('occupe', 'Occupée'),
        ('maintenance', 'Maintenance'),
    ]
    chambre_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hopital = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    numero_chambre = models.CharField(max_length=20)
    etage = models.IntegerField()
    capacite = models.IntegerField()  # nombre de lits
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='disponible')

    class Meta:
        unique_together = ('hopital', 'numero_chambre')
        db_table = 'chambre'

    def __str__(self):
        return f"{self.numero_chambre} (Étage {self.etage})"


class Lit(models.Model):
    """Lit dans une chambre"""
    STATUT_CHOICES = [
        ('libre', 'Libre'),
        ('occupe', 'Occupé'),
        ('nettoyage', 'Nettoyage'),
    ]
    lit_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chambre = models.ForeignKey(Chambre, on_delete=models.CASCADE, related_name='lits')
    numero_lit = models.CharField(max_length=20)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='libre')

    class Meta:
        db_table = 'lit'

    def __str__(self):
        return f"Lit {self.numero_lit} - {self.chambre.numero_chambre}"


class Hospitalisation(models.Model):
    """Séjour d'un patient"""
    STATUT_CHOICES = [
        ('en_cours', 'En cours'),
        ('termine', 'Terminé'),
        ('annule', 'Annulé'),
    ]
    hospitalisation_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hopital = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='hospitalisations')
    lit = models.ForeignKey(Lit, on_delete=models.PROTECT)
    date_entree = models.DateTimeField(auto_now_add=True)
    date_sortie = models.DateTimeField(null=True, blank=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_cours')
    motif = models.TextField(blank=True)

    class Meta:
        db_table = 'hospitalisation'

    def __str__(self):
        return f"{self.patient} - {self.date_entree.date()}"
from django.contrib import admin
from .models import Chambre, Lit, Hospitalisation

@admin.register(Chambre)
class ChambreAdmin(admin.ModelAdmin):
    list_display = ('numero_chambre', 'etage', 'capacite', 'statut')
    list_filter = ('hopital', 'statut')
    search_fields = ('numero_chambre',)

@admin.register(Lit)
class LitAdmin(admin.ModelAdmin):
    list_display = ('numero_lit', 'chambre', 'statut')
    list_filter = ('statut',)

@admin.register(Hospitalisation)
class HospitalisationAdmin(admin.ModelAdmin):
    list_display = ('patient', 'lit', 'date_entree', 'date_sortie', 'statut')
    list_filter = ('statut', 'hopital')
from django.contrib import admin
from .models import TypeSalle, SalleMedicale, Equipement, PlanningSalle, AffectationSalle

@admin.register(TypeSalle)
class TypeSalleAdmin(admin.ModelAdmin):
    list_display = ('nom', 'hopital')
    list_filter = ('hopital',)

@admin.register(SalleMedicale)
class SalleMedicaleAdmin(admin.ModelAdmin):
    list_display = ('nom', 'type_salle', 'statut', 'est_active')
    list_filter = ('hopital', 'type_salle', 'statut')

@admin.register(Equipement)
class EquipementAdmin(admin.ModelAdmin):
    list_display = ('nom', 'hopital')
    list_filter = ('hopital',)

@admin.register(PlanningSalle)
class PlanningSalleAdmin(admin.ModelAdmin):
    list_display = ('salle', 'date', 'heure_debut', 'medecin', 'statut')
    list_filter = ('statut', 'date')

@admin.register(AffectationSalle)
class AffectationSalleAdmin(admin.ModelAdmin):
    list_display = ('salle', 'medecin', 'date_debut', 'date_fin', 'actif')
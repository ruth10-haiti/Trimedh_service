from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import Utilisateur

@admin.register(Utilisateur)
class UtilisateurAdmin(BaseUserAdmin):
    list_display = ('avatar', 'email', 'nom_complet', 'role_badge', 'hopital', 'status_badge', 'cree_le')
    list_filter = ('role', 'is_active', 'hopital', 'is_staff')
    search_fields = ('email', 'nom_complet')
    ordering = ('-cree_le',)
    list_per_page = 20
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Informations personnelles', {'fields': ('nom_complet',)}),
        ('Rôle et accès', {'fields': ('role', 'hopital', 'is_active', 'is_staff', 'is_superuser')}),
        ('Permissions', {'fields': ('groups', 'user_permissions')}),
        ('Dates importantes', {'fields': ('last_login', 'cree_le', 'derniere_connexion')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'nom_complet', 'password1', 'password2', 'role', 'hopital'),
        }),
    )
    
    readonly_fields = ('cree_le', 'last_login', 'derniere_connexion')
    
    def avatar(self, obj):
        """Affiche un avatar avec les initiales"""
        initials = ''.join([word[0].upper() for word in obj.nom_complet.split()[:2]])
        colors = {
            'admin-systeme': '#dc3545',
            'proprietaire-hopital': '#007bff',
            'medecin': '#28a745',
            'infirmier': '#fd7e14',
            'secretaire': '#6f42c1',
            'personnel': '#6c757d',
            'patient': '#17a2b8',
        }
        color = colors.get(obj.role, '#6c757d')
        return format_html(
            '<div style="background-color: {}; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 13px;">{}</div>',
            color,
            initials
        )
    avatar.short_description = ''
    
    def role_badge(self, obj):
        """Affiche le rôle avec un badge coloré"""
        colors = {
            'admin-systeme': '#dc3545',
            'proprietaire-hopital': '#007bff',
            'medecin': '#28a745',
            'infirmier': '#fd7e14',
            'secretaire': '#6f42c1',
            'personnel': '#6c757d',
            'patient': '#17a2b8',
        }
        color = colors.get(obj.role, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px;">{}</span>',
            color,
            obj.get_role_display()
        )
    role_badge.short_description = 'Rôle'
    
    def status_badge(self, obj):
        """Affiche le statut avec un badge coloré"""
        if obj.is_active:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px;">✓ Actif</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px;">✗ Inactif</span>'
            )
    status_badge.short_description = 'Statut'
    
    actions = ['activer_utilisateurs', 'desactiver_utilisateurs']
    
    def activer_utilisateurs(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} utilisateur(s) activé(s).')
    activer_utilisateurs.short_description = 'Activer les utilisateurs sélectionnés'
    
    def desactiver_utilisateurs(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} utilisateur(s) désactivé(s).')
    desactiver_utilisateurs.short_description = 'Désactiver les utilisateurs sélectionnés'
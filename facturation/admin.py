# admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Plan, AbonnementStatut, PaiementMethode, PaiementStatut,
    InvoiceStatut, Abonnement, Paiement, Invoice,
    AbonnementRenouvellement, EssaiGratuit, Coupon, CouponTenant,
    TarifConsultation
)

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('nom', 'price_badge', 'actif_badge', 'created_at')
    list_filter = ('actif',)
    search_fields = ('nom', 'description')
    list_per_page = 20
    
    fieldsets = (
        ('Informations Générales', {
            'fields': ('nom', 'description')
        }),
        ('Tarification', {
            'fields': ('prix_mensuel', 'prix_annuel')
        }),
        ('Configuration', {
            'fields': ('actif',)
        }),
    )
    
    def price_badge(self, obj):
        """Affiche les prix avec des badges"""
        return format_html(
            '<div><span style="background-color: #28a745; color: white; padding: 3px 8px; border-radius: 12px; font-size: 11px;">Mensuel: {}€</span><br>'
            '<span style="background-color: #007bff; color: white; padding: 3px 8px; border-radius: 12px; font-size: 11px; margin-top: 3px; display: inline-block;">Annuel: {}€</span></div>',
            obj.prix_mensuel,
            obj.prix_annuel
        )
    price_badge.short_description = 'Tarifs'
    
    def actif_badge(self, obj):
        """Affiche le statut avec un badge"""
        if obj.actif:
            return format_html('<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px;">✓ Actif</span>')
        return format_html('<span style="background-color: #dc3545; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px;">✗ Inactif</span>')
    actif_badge.short_description = 'Statut'


@admin.register(Abonnement)
class AbonnementAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'plan', 'statut_badge', 'periode', 'created_at')
    list_filter = ('statut', 'plan')
    search_fields = ('tenant__nom', 'plan__nom')
    list_per_page = 20
    
    fieldsets = (
        ('Informations Générales', {
            'fields': ('tenant', 'plan', 'statut')
        }),
        ('Période', {
            'fields': ('date_debut', 'date_fin')
        }),
        ('Système', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at')
    
    def statut_badge(self, obj):
        """Affiche le statut avec un badge coloré"""
        colors = {
            'actif': '#28a745',
            'expire': '#dc3545',
            'suspendu': '#fd7e14',
            'annule': '#6c757d',
        }
        color = colors.get(obj.statut, '#6c757d')
        icons = {
            'actif': '✓',
            'expire': '⚠',
            'suspendu': '⏸',
            'annule': '✗',
        }
        icon = icons.get(obj.statut, '•')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px;">{} {}</span>',
            color,
            icon,
            obj.get_statut_display()
        )
    statut_badge.short_description = 'Statut'
    
    def periode(self, obj):
        """Affiche la période d'abonnement"""
        if obj.date_debut and obj.date_fin:
            return format_html(
                '<span style="font-size: 11px;">{}<br>→<br>{}</span>',
                obj.date_debut.strftime('%d/%m/%Y'),
                obj.date_fin.strftime('%d/%m/%Y')
            )
        return '-'
    periode.short_description = 'Période'


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'abonnement', 'montant_badge', 'methode_badge', 'statut_badge', 'date_paiement')
    list_filter = ('methode', 'statut', 'date_paiement')
    search_fields = ('tenant__nom', 'reference', 'abonnement__plan__nom')
    list_per_page = 20
    
    fieldsets = (
        ('Informations Générales', {
            'fields': ('tenant', 'abonnement', 'methode', 'statut')
        }),
        ('Détails Paiement', {
            'fields': ('montant', 'date_paiement', 'reference')
        }),
        ('Système', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at',)
    
    def montant_badge(self, obj):
        """Affiche le montant avec un badge"""
        return format_html(
            '<span style="background-color: #17a2b8; color: white; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: bold;">{} €</span>',
            obj.montant
        )
    montant_badge.short_description = 'Montant'
    
    def methode_badge(self, obj):
        """Affiche la méthode de paiement avec un badge"""
        colors = {
            'carte': '#007bff',
            'virement': '#28a745',
            'mobile_money': '#fd7e14',
            'especes': '#6c757d',
        }
        color = colors.get(obj.methode, '#6c757d')
        icons = {
            'carte': '💳',
            'virement': '🏦',
            'mobile_money': '📱',
            'especes': '💰',
        }
        icon = icons.get(obj.methode, '💵')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px;">{} {}</span>',
            color,
            icon,
            obj.get_methode_display()
        )
    methode_badge.short_description = 'Méthode'
    
    def statut_badge(self, obj):
        """Affiche le statut du paiement avec un badge"""
        if obj.statut == 'reussi':
            return format_html('<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px;">✓ Réussi</span>')
        elif obj.statut == 'echoue':
            return format_html('<span style="background-color: #dc3545; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px;">✗ Échoué</span>')
        elif obj.statut == 'en_attente':
            return format_html('<span style="background-color: #fd7e14; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px;">⏳ En attente</span>')
        elif obj.statut == 'rembourse':
            return format_html('<span style="background-color: #6c757d; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px;">↺ Remboursé</span>')
        return format_html('<span style="background-color: #6c757d; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px;">{}</span>', obj.get_statut_display())
    statut_badge.short_description = 'Statut'


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('numero_facture', 'tenant', 'montant_badge', 'statut_badge', 'date_emission', 'lien_pdf')
    list_filter = ('statut', 'date_emission')
    search_fields = ('numero_facture', 'tenant__nom')
    list_per_page = 20
    
    fieldsets = (
        ('Informations Générales', {
            'fields': ('paiement', 'tenant', 'statut')
        }),
        ('Détails Facture', {
            'fields': ('numero_facture', 'date_emission', 'date_echeance', 'montant', 'url_pdf')
        }),
        ('Système', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at')
    
    def montant_badge(self, obj):
        """Affiche le montant avec un badge"""
        return format_html(
            '<span style="background-color: #17a2b8; color: white; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: bold;">{} €</span>',
            obj.montant
        )
    montant_badge.short_description = 'Montant'
    
    def statut_badge(self, obj):
        """Affiche le statut de la facture avec un badge"""
        colors = {
            'payee': '#28a745',
            'en_attente': '#fd7e14',
            'en_retard': '#dc3545',
            'annulee': '#6c757d',
        }
        color = colors.get(obj.statut, '#6c757d')
        icons = {
            'payee': '✓',
            'en_attente': '⏳',
            'en_retard': '⚠',
            'annulee': '✗',
        }
        icon = icons.get(obj.statut, '📄')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px;">{} {}</span>',
            color,
            icon,
            obj.get_statut_display()
        )
    statut_badge.short_description = 'Statut'
    
    def lien_pdf(self, obj):
        """Affiche un lien pour télécharger le PDF"""
        if obj.url_pdf:
            return format_html(
                '<a href="{}" target="_blank" style="background-color: #dc3545; color: white; padding: 3px 8px; border-radius: 12px; text-decoration: none; font-size: 11px;">📄 PDF</a>',
                obj.url_pdf
            )
        return '-'
    lien_pdf.short_description = 'PDF'
    
    actions = ['marquer_comme_payee', 'marquer_comme_en_attente']
    
    def marquer_comme_payee(self, request, queryset):
        count = queryset.update(statut='payee')
        self.message_user(request, f'{count} facture(s) marquée(s) comme payée(s).')
    marquer_comme_payee.short_description = 'Marquer comme payée'
    
    def marquer_comme_en_attente(self, request, queryset):
        count = queryset.update(statut='en_attente')
        self.message_user(request, f'{count} facture(s) marquée(s) comme en attente.')
    marquer_comme_en_attente.short_description = 'Marquer comme en attente'


# Enregistrement des autres modèles si nécessaire
@admin.register(AbonnementRenouvellement)
class AbonnementRenouvellementAdmin(admin.ModelAdmin):
    list_display = ('abonnement', 'date_renouvellement', 'created_at')
    list_filter = ('date_renouvellement',)
    
    def has_add_permission(self, request):
        return False


@admin.register(EssaiGratuit)
class EssaiGratuitAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'date_debut', 'date_fin', 'actif')
    list_filter = ('actif', 'date_debut')


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'reduction', 'type_reduction', 'valable_jusque', 'actif')
    list_filter = ('actif', 'type_reduction', 'valable_jusque')
    search_fields = ('code',)


@admin.register(TarifConsultation)
class TarifConsultationAdmin(admin.ModelAdmin):
    list_display = ('hopital', 'type_consultation', 'prix', 'actif')
    list_filter = ('actif', 'type_consultation')
    search_fields = ('hopital__nom',)
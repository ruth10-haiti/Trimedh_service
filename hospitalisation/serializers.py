from rest_framework import serializers
from .models import Chambre, Lit, Hospitalisation

class ChambreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chambre
        fields = '__all__'
        read_only_fields = ('chambre_id',)

class LitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lit
        fields = '__all__'
        read_only_fields = ('lit_id',)

class HospitalisationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hospitalisation
        fields = '__all__'
        read_only_fields = ('hospitalisation_id', 'date_entree')
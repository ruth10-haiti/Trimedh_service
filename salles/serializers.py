from rest_framework import serializers
from .models import TypeSalle, SalleMedicale, Equipement, PlanningSalle, AffectationSalle

class TypeSalleSerializer(serializers.ModelSerializer):
    class Meta:
        model = TypeSalle
        fields = '__all__'

class SalleMedicaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalleMedicale
        fields = '__all__'

class EquipementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipement
        fields = '__all__'

class PlanningSalleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanningSalle
        fields = '__all__'

class AffectationSalleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AffectationSalle
        fields = '__all__'
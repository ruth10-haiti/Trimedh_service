from rest_framework.routers import DefaultRouter
from .views import (
    TypeSalleViewSet, SalleMedicaleViewSet, EquipementViewSet,
    PlanningSalleViewSet, AffectationSalleViewSet
)

router = DefaultRouter()
router.register(r'types-salle', TypeSalleViewSet, basename='typesalle')
router.register(r'salles', SalleMedicaleViewSet, basename='sallemedicale')
router.register(r'equipements', EquipementViewSet, basename='equipement')
router.register(r'planning', PlanningSalleViewSet, basename='planning')
router.register(r'affectations', AffectationSalleViewSet, basename='affectation')

urlpatterns = router.urls
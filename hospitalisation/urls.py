from rest_framework.routers import DefaultRouter
from .views import ChambreViewSet, LitViewSet, HospitalisationViewSet

router = DefaultRouter()
router.register(r'chambres', ChambreViewSet, basename='chambre')
router.register(r'lits', LitViewSet, basename='lit')
router.register(r'hospitalisations', HospitalisationViewSet, basename='hospitalisation')

urlpatterns = router.urls
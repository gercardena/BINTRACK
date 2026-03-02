from rest_framework.routers import DefaultRouter
from .views import FacturaViewSet

router = DefaultRouter()
router.register(r"", FacturaViewSet, basename="facturas")

urlpatterns = router.urls
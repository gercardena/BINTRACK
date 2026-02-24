from rest_framework.routers import DefaultRouter
from .views import SaleViewSet, SaleItemViewSet

router = DefaultRouter()
router.register(r"sales", SaleViewSet, basename="sales")
router.register(r"items", SaleItemViewSet, basename="items")

urlpatterns = router.urls
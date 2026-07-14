from rest_framework.routers import DefaultRouter

from .views import ProductListingViewSet, SourcingRequestViewSet, SupplierViewSet

router = DefaultRouter()
router.register('sourcing-requests', SourcingRequestViewSet, basename='sourcing-request')
router.register('suppliers', SupplierViewSet, basename='supplier')
router.register('products', ProductListingViewSet, basename='product')

urlpatterns = router.urls

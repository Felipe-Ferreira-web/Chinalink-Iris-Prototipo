from rest_framework.routers import DefaultRouter

from .views import ContactExtractionViewSet

router = DefaultRouter()
router.register('extractions', ContactExtractionViewSet, basename='contact-extraction')

urlpatterns = router.urls

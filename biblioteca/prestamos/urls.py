from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('prestamos', views.PrestamoViewSet, basename='prestamo')

urlpatterns = router.urls

from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('solicitudes', views.SolicitudPrestamoViewSet, basename='solicitud')

urlpatterns = router.urls

from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('reportes', views.ReportesViewSet, basename='reporte')
urlpatterns = router.urls

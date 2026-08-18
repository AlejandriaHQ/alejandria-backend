from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('categorias', views.CategoriaViewSet, basename='categoria')

urlpatterns = router.urls

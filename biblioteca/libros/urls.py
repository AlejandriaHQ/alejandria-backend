from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('libros', views.LibroViewSet, basename='libro')

urlpatterns = router.urls

from django.contrib import admin
from django.urls import path, re_path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# 1. Configuración de la vista del esquema (Swagger)
schema_view = get_schema_view(
    openapi.Info(
        title="Api Alejandria ",
        default_version='v1',
        description="Descripción de mi API",
        terms_of_service="https://www.tus-terminos.com/",
        contact=openapi.Contact(email="contacto@tudominio.com"),
        license=openapi.License(name="Licencia XYZ"),
    ),
    public=False,
    permission_classes=(permissions.AllowAny,),
)

# 2. Rutas Globales
urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Rutas para la documentación (Swagger y ReDoc)
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0)),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0)),
    
    # Rutas de nuestra aplicación
    path('biblioteca/', include('biblioteca.Categorias.urlsCategorias')),
]
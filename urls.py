from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

# 1. Rutas Globales
urlpatterns = [
    path('admin/', admin.site.urls),

    # Rutas para la documentación (Swagger y ReDoc)
    path('swagger/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='schema-swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='schema-redoc'),

    # Rutas de nuestra aplicación
    path('biblioteca/Categorias/', include('biblioteca.Categorias.urlsCategorias')),
    path('biblioteca/libros/', include('biblioteca.Libros.urlsLibros')),
    path('biblioteca/usuarios/', include('biblioteca.Usuarios.urlsUsuarios')),
    path('biblioteca/prestamos/', include('biblioteca.Prestamos.urlsPrestamos')),
]
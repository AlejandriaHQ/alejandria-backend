from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(['GET'])
def inicio(request):
    """Vista de bienvenida en la raíz del API."""
    return Response({
        "success": True,
        "Mensaje": "Bienvenido a la API de Alejandría",
        "datos": {
            "documentacion": {
                "swagger": "/swagger/",
                "redoc": "/redoc/",
                "schema": "/swagger/schema/",
            },
            "endpoints": {
                "categorias": "/biblioteca/Categorias/",
                "libros": "/biblioteca/libros/",
                "usuarios": "/biblioteca/usuarios/",
                "prestamos": "/biblioteca/prestamos/",
            },
        },
    })

# 1. Rutas Globales
urlpatterns = [
    path('', inicio, name='inicio'),
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
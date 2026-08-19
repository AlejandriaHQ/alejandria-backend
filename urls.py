from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


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
                "categorias": "/biblioteca/categorias/",
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
    path('biblioteca/', include('biblioteca.categorias.urls')),
    path('biblioteca/', include('biblioteca.libros.urls')),
    path('biblioteca/', include('biblioteca.usuarios.urls')),
    path('biblioteca/', include('biblioteca.prestamos.urls')),

    # Autenticación JWT (obtener y refrescar tokens)
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

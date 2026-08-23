from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenRefreshView

from biblioteca.usuarios.token import CustomTokenObtainPairView


@api_view(['GET'])
@permission_classes([AllowAny])
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
    # F15 pentest: / expone el mapa de endpoints. Con JWT activo (IsAuthenticated
    # global en settings) el acceso anónimo responde 401, por lo que el mapa solo
    # es visible para clientes autenticados. Decisión: se MANTIENE — es útil para
    # desarrolladores y ya no filtra información a clientes no autenticados.
    path('', inicio, name='inicio'),
    # /admin/ (F08 pentest): el Django admin nativo NO tiene protección contra
    # fuerza bruta por defecto. En producción debe restringirse por red/IP o
    # añadir django-axes. NO exponerlo públicamente.
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
    path('biblioteca/', include('biblioteca.reportes.urls')),

    # Autenticación JWT: /token/ acepta email O identifier + password
    # (CustomTokenObtainPairSerializer) y devuelve access con claim 'role';
    # /token/refresh/ mantiene el refresco estándar.
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

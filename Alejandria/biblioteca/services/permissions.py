from urllib import request

from rest_framework.permissions import BasePermission

class IsAdminUser(BasePermission):
    """
    solo administradores.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_staff)
    
    
class IsAuthenticated(BasePermission):
    """
    solo usuarios autenticados.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)
    
class IsOwnerOrAdmin(BasePermission):
    """
    Dueño del objeto o administrador.
    """
    def has_object_permission(self, request, view, obj):
        # Permitir acceso si el usuario es administrador
        if request.user.is_staff:
            return True
        if hasattr(obj, 'usuario'):
            # Permitir acceso si el usuario es el propietario del objeto
            return obj.usuario == request.user
        return False
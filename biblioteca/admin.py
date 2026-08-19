from django.contrib import admin
from .models import Categoria, Libro, Usuario, Prestamo


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre', 'descripcion')


@admin.register(Libro)
class LibroAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'autor', 'isbn', 'cantidad', 'id_categoria')
    search_fields = ('titulo', 'autor', 'isbn')
    list_filter = ('id_categoria',)


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'role', 'cedula', 'phone', 'identifier', 'is_staff')
    search_fields = ('first_name', 'last_name', 'email', 'cedula', 'phone', 'identifier')
    list_filter = ('role', 'is_staff')
    # No se expone la contraseña (ni en el formulario ni en la lista);
    # AbstractUser ya oculta el password y lo gestiona el framework.
    exclude = ('password',)


@admin.register(Prestamo)
class PrestamoAdmin(admin.ModelAdmin):
    list_display = ('id_usuario', 'id_libro', 'fecha_prestamo', 'fecha_devolucion', 'estado')
    search_fields = ('id_usuario__first_name', 'id_usuario__last_name', 'id_libro__titulo', 'estado')
    list_filter = ('estado', 'fecha_prestamo')

"""Helpers compartidos para la suite de tests del API de la biblioteca.

Proporciona la base ``BaseAPITest`` con creadores de fixtures y
aserciones del envelope JSON que usa el API
(``{"success": bool, "Mensaje": str, "datos": any}``).
"""
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from rest_framework.test import APITestCase

from biblioteca.models import Categoria, Libro, Prestamo, Usuario

# Contador para generar correos únicos automáticamente en los fixtures.
_correo_counter = 0


class BaseAPITest(APITestCase):
    """Base con helpers para crear fixtures y verificar el envelope JSON."""

    # ------------------------------------------------------------------ #
    # Configuración
    # ------------------------------------------------------------------ #
    def setUp(self):
        super().setUp()
        # La API exige autenticación (IsAuthenticated por defecto) y solo
        # admite ESCRITURA de usuarios con role='admin' o is_staff. Se
        # autentica el cliente con force_authenticate como un admin NO
        # persistido: el guard de la vista ve role/is_staff, pero el admin
        # no contamina listados ni conteos (no aparece en Usuario.objects).
        self.auth_user = get_user_model()(
            username='admin-auth-test',
            email='admin-auth@test.com',
            first_name='Admin',
            last_name='Auth',
            role='admin',
            is_staff=True,
        )
        self.client.force_authenticate(user=self.auth_user)

    def autenticar_como(self, usuario):
        """Autentica el cliente como un usuario arbitrario (force_authenticate).

        force_authenticate fija request.user directamente y anula cualquier
        token JWT previo, por lo que reemplaza limpiamente al admin del setUp
        (p. ej. para probar la protección por rol con un usuario común).
        """
        self.client.force_authenticate(user=usuario)

    # ------------------------------------------------------------------ #
    # Fixtures
    # ------------------------------------------------------------------ #
    def crear_categoria(self, nombre="Categoría test", descripcion="Descripción de prueba"):
        return Categoria.objects.create(nombre=nombre, descripcion=descripcion)

    def crear_libro(self, titulo="Libro de prueba", autor="Autor de prueba",
                    isbn=None, cantidad=5, categoria=None):
        if categoria is None:
            categoria = self.crear_categoria()
        return Libro.objects.create(
            titulo=titulo,
            autor=autor,
            isbn=isbn,
            cantidad=cantidad,
            id_categoria=categoria,
        )

    def crear_usuario(self, first_name="Juan", last_name="Perez", email=None,
                      password="secreto123", role="user", cedula=None,
                      phone=None, address=None):
        global _correo_counter
        if email is None:
            _correo_counter += 1
            email = f"usuario{_correo_counter}@test.com"
        # set_password es OBLIGATORIO: AbstractUser no hashea en save().
        usuario = Usuario(
            first_name=first_name,
            last_name=last_name,
            email=email,
            role=role,
            cedula=cedula,
            phone=phone,
            address=address,
        )
        usuario.set_password(password)
        usuario.save()
        return usuario

    def crear_prestamo(self, usuario=None, libro=None, fecha_prestamo=None,
                       fecha_devolucion=None, estado=Prestamo.ESTADO_PRESTADO):
        if usuario is None:
            usuario = self.crear_usuario()
        if libro is None:
            libro = self.crear_libro()
        if fecha_prestamo is None:
            fecha_prestamo = date.today() - timedelta(days=1)
        return Prestamo.objects.create(
            id_usuario=usuario,
            id_libro=libro,
            fecha_prestamo=fecha_prestamo,
            fecha_devolucion=fecha_devolucion,
            estado=estado,
        )

    # ------------------------------------------------------------------ #
    # Aserciones del envelope
    # ------------------------------------------------------------------ #
    def assert_envelope_exitosa(self, response, status=HTTP_200_OK):
        """Verifica un envelope de éxito con el status code esperado."""
        self.assertEqual(response.status_code, status)
        self.assertTrue(response.data['success'])
        self.assertIn('Mensaje', response.data)
        self.assertIn('datos', response.data)

    def assert_envelope_error(self, response, status=HTTP_400_BAD_REQUEST):
        """Verifica un envelope de error con el status code esperado."""
        self.assertEqual(response.status_code, status)
        self.assertFalse(response.data['success'])
        self.assertIn('Mensaje', response.data)
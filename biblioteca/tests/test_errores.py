"""Cobertura de errores y validaciones del API.

Verifica: duplicados (correo en Usuario, isbn en Libro) -> 400, registros
inexistentes -> 404, cantidad de Libro <= 0 -> 400, fechas inválidas en
Prestamo -> 400, y que la contraseña de Usuario nunca aparezca en las
respuestas (write_only) y se almacene hasheada.
"""
from datetime import date, timedelta

from django.urls import reverse
from rest_framework.status import (
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_404_NOT_FOUND,
)

from biblioteca.models import Prestamo
from biblioteca.tests.helpers import BaseAPITest


class CategoriasErroresTests(BaseAPITest):
    """Errores del recurso Categorias."""

    def test_view_inexistente(self):
        response = self.client.get(reverse('categoria-detail', args=[9999]))

        self.assert_envelope_error(response, HTTP_404_NOT_FOUND)

    def test_update_inexistente(self):
        response = self.client.put(
            reverse('categoria-detail', args=[9999]),
            {'nombre': 'Ficción', 'descripcion': 'd'},
            format='json',
        )

        self.assert_envelope_error(response, HTTP_404_NOT_FOUND)

    def test_delete_inexistente(self):
        response = self.client.delete(reverse('categoria-detail', args=[9999]))

        self.assert_envelope_error(response, HTTP_404_NOT_FOUND)

    def test_crear_sin_nombre(self):
        response = self.client.post(
            reverse('categoria-list'), {'descripcion': 'sin nombre'}, format='json')

        self.assert_envelope_error(response)

    def test_update_sin_nombre(self):
        categoria = self.crear_categoria(nombre='Ficción')

        response = self.client.put(
            reverse('categoria-detail', args=[categoria.id_categoria]),
            {'descripcion': 'solo descripcion'},
            format='json',
        )

        self.assert_envelope_error(response)

    def test_eliminar_categoria_con_libros_asociados(self):
        # ProtectedError: no se puede eliminar una categoría con libros.
        categoria = self.crear_categoria(nombre='Ficción')
        self.crear_libro(titulo='Dune', isbn='978-1', categoria=categoria)

        response = self.client.delete(
            reverse('categoria-detail', args=[categoria.id_categoria]))

        self.assert_envelope_error(response)


class LibrosErroresTests(BaseAPITest):
    """Errores del recurso Libros."""

    def setUp(self):
        super().setUp()
        self.categoria = self.crear_categoria(nombre='Ficción')

    def test_isbn_duplicado(self):
        self.crear_libro(titulo='Dune', isbn='978-1', categoria=self.categoria)

        response = self.client.post(
            reverse('libro-list'),
            {'titulo': 'Otro libro', 'autor': 'Otro autor', 'isbn': '978-1',
             'id_categoria': self.categoria.id_categoria},
            format='json',
        )

        self.assert_envelope_error(response)
        # El mensaje es claro (duplicado), no el genérico "Complete los campos vacios".
        self.assertEqual(response.data['Mensaje']['isbn'][0],
                         'Ya existe un libro con ese ISBN')

    def test_cantidad_cero(self):
        response = self.client.post(
            reverse('libro-list'),
            {'titulo': 'Dune', 'autor': 'Frank Herbert', 'isbn': '978-2',
             'cantidad': 0, 'id_categoria': self.categoria.id_categoria},
            format='json',
        )

        self.assert_envelope_error(response)

    def test_cantidad_negativa(self):
        response = self.client.post(
            reverse('libro-list'),
            {'titulo': 'Dune', 'autor': 'Frank Herbert', 'isbn': '978-3',
             'cantidad': -3, 'id_categoria': self.categoria.id_categoria},
            format='json',
        )

        self.assert_envelope_error(response)

    def test_crear_sin_campos_requeridos(self):
        response = self.client.post(
            reverse('libro-list'),
            {'titulo': 'Dune', 'id_categoria': self.categoria.id_categoria},
            format='json',
        )

        self.assert_envelope_error(response)

    def test_view_inexistente(self):
        response = self.client.get(reverse('libro-detail', args=[9999]))

        self.assert_envelope_error(response, HTTP_404_NOT_FOUND)

    def test_update_inexistente(self):
        response = self.client.put(
            reverse('libro-detail', args=[9999]),
            {'titulo': 'Dune', 'autor': 'A',
             'id_categoria': self.categoria.id_categoria},
            format='json',
        )

        self.assert_envelope_error(response, HTTP_404_NOT_FOUND)

    def test_delete_inexistente(self):
        response = self.client.delete(reverse('libro-detail', args=[9999]))

        self.assert_envelope_error(response, HTTP_404_NOT_FOUND)

    def test_pagina_fuera_de_rango(self):
        # Un envelope de error de paginación debe ser consistente con
        # Result.Error: 'datos' es None (no string vacío).
        url = f"{reverse('libro-paginar')}?page=99"
        response = self.client.get(url)

        self.assert_envelope_error(response)
        self.assertIsNone(response.data['datos'])
        self.assertIn('maxPages', response.data)


class UsuariosErroresTests(BaseAPITest):
    """Errores del recurso Usuarios, incluyendo el manejo de contraseñas."""

    PASSWORD_PLANA = 'clave-super-secreta-42'

    def test_correo_duplicado(self):
        self.crear_usuario(correo='juan@test.com')

        response = self.client.post(
            reverse('usuario-list'),
            {'nombre': 'Juan', 'apellido': 'Perez', 'correo': 'juan@test.com',
             'password': 'otra-clave-1'},
            format='json',
        )

        self.assert_envelope_error(response)
        # El mensaje es claro (duplicado), no el genérico "Complete los campos vacios".
        self.assertEqual(response.data['Mensaje']['correo'][0],
                         'Ya existe un usuario con ese correo')

    def test_crear_sin_password(self):
        response = self.client.post(
            reverse('usuario-list'),
            {'nombre': 'Juan', 'apellido': 'Perez', 'correo': 'juan@test.com'},
            format='json',
        )

        self.assert_envelope_error(response)

    def test_view_inexistente(self):
        response = self.client.get(reverse('usuario-detail', args=[9999]))

        self.assert_envelope_error(response, HTTP_404_NOT_FOUND)

    def test_update_inexistente(self):
        response = self.client.put(
            reverse('usuario-detail', args=[9999]),
            {'nombre': 'Juan', 'apellido': 'Perez',
             'correo': 'juan@test.com', 'password': 'clave-1'},
            format='json',
        )

        self.assert_envelope_error(response, HTTP_404_NOT_FOUND)

    def test_delete_inexistente(self):
        response = self.client.delete(reverse('usuario-detail', args=[9999]))

        self.assert_envelope_error(response, HTTP_404_NOT_FOUND)

    def test_password_no_aparece_al_crear(self):
        response = self.client.post(
            reverse('usuario-list'),
            {'nombre': 'Juan', 'apellido': 'Perez', 'correo': 'juan@test.com',
             'password': self.PASSWORD_PLANA},
            format='json',
        )

        self.assert_envelope_exitosa(response, HTTP_201_CREATED)
        self.assertNotIn('password', response.data['datos'])
        self.assertNotIn(self.PASSWORD_PLANA, str(response.data))

    def test_password_no_aparece_en_lista_ni_view(self):
        usuario = self.crear_usuario(correo='juan@test.com',
                                     password=self.PASSWORD_PLANA)

        response_lista = self.client.get(reverse('usuario-list'))
        self.assert_envelope_exitosa(response_lista)
        self.assertNotIn(self.PASSWORD_PLANA, str(response_lista.data))
        for item in response_lista.data['datos']:
            self.assertNotIn('password', item)

        response_view = self.client.get(
            reverse('usuario-detail', args=[usuario.id_usuario]))
        self.assert_envelope_exitosa(response_view)
        self.assertNotIn(self.PASSWORD_PLANA, str(response_view.data))
        self.assertNotIn('password', response_view.data['datos'])

    def test_password_almacenada_hasheada(self):
        usuario = self.crear_usuario(correo='juan@test.com',
                                     password=self.PASSWORD_PLANA)

        self.assertNotEqual(usuario.password, self.PASSWORD_PLANA)
        self.assertTrue(usuario.password.startswith('pbkdf2_'))
        self.assertTrue(usuario.check_password(self.PASSWORD_PLANA))


class PrestamosErroresTests(BaseAPITest):
    """Errores del recurso Prestamos."""

    def setUp(self):
        super().setUp()
        self.usuario = self.crear_usuario(correo='juan@test.com')
        self.libro = self.crear_libro(titulo='Dune', isbn='978-1', cantidad=5)

    def test_fecha_devolucion_anterior_a_fecha_prestamo(self):
        hoy = date.today()
        response = self.client.post(
            reverse('prestamo-list'),
            {'id_usuario': self.usuario.id_usuario,
             'id_libro': self.libro.id_libro,
             'fecha_prestamo': hoy.isoformat(),
             'fecha_devolucion': (hoy - timedelta(days=1)).isoformat()},
            format='json',
        )

        self.assert_envelope_error(response)

    def test_view_inexistente(self):
        response = self.client.get(reverse('prestamo-detail', args=[9999]))

        self.assert_envelope_error(response, HTTP_404_NOT_FOUND)

    def test_update_inexistente(self):
        hoy = date.today()
        response = self.client.put(
            reverse('prestamo-detail', args=[9999]),
            {'id_usuario': self.usuario.id_usuario,
             'id_libro': self.libro.id_libro,
             'fecha_prestamo': hoy.isoformat()},
            format='json',
        )

        self.assert_envelope_error(response, HTTP_404_NOT_FOUND)

    def test_delete_inexistente(self):
        response = self.client.delete(reverse('prestamo-detail', args=[9999]))

        self.assert_envelope_error(response, HTTP_404_NOT_FOUND)

    def test_crear_sin_campos_requeridos(self):
        response = self.client.post(
            reverse('prestamo-list'),
            {'id_usuario': self.usuario.id_usuario},
            format='json',
        )

        self.assert_envelope_error(response)

    def test_update_fecha_devolucion_invalida(self):
        prestamo = self.crear_prestamo(usuario=self.usuario, libro=self.libro)
        hoy = date.today()
        response = self.client.put(
            reverse('prestamo-detail', args=[prestamo.id_prestamo]),
            {'id_usuario': self.usuario.id_usuario,
             'id_libro': self.libro.id_libro,
             'fecha_prestamo': hoy.isoformat(),
             'fecha_devolucion': (hoy - timedelta(days=2)).isoformat()},
            format='json',
        )

        self.assert_envelope_error(response)
        # El préstamo no debe haber cambiado.
        prestamo.refresh_from_db()
        self.assertEqual(prestamo.estado, Prestamo.ESTADO_PRESTADO)


class AccesoAnonimoTests(BaseAPITest):
    """La API ya no es anónima: sin token JWT se rechaza con 401 (F01)."""

    def test_sin_token_devuelve_401(self):
        # Se limpian las credenciales que setUp dejó en el cliente.
        self.client.credentials()

        response = self.client.get(reverse('categoria-list'))

        self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED)

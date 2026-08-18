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
    HTTP_404_NOT_FOUND,
)

from biblioteca.models import Prestamo
from biblioteca.tests.helpers import BaseAPITest


class CategoriasErroresTests(BaseAPITest):
    """Errores del recurso Categorias."""

    def test_view_sin_id(self):
        response = self.client.get(reverse('Categoria_view'))

        self.assert_envelope_error(response)

    def test_view_inexistente(self):
        url = f"{reverse('Categoria_view')}?id_categoria=9999"
        response = self.client.get(url)

        self.assert_envelope_error(response, HTTP_404_NOT_FOUND)

    def test_update_inexistente(self):
        response = self.client.put(
            reverse('Categoria_update'),
            {'id_categoria': 9999, 'nombre': 'Ficción', 'descripcion': 'd'},
            format='json',
        )

        self.assert_envelope_error(response, HTTP_404_NOT_FOUND)

    def test_delete_inexistente(self):
        url = f"{reverse('Categoria_delete')}?id_categoria=9999"
        response = self.client.delete(url)

        self.assert_envelope_error(response, HTTP_404_NOT_FOUND)

    def test_crear_sin_nombre(self):
        response = self.client.post(
            reverse('Categoria_add'), {'descripcion': 'sin nombre'}, format='json')

        self.assert_envelope_error(response)

    def test_update_sin_id(self):
        response = self.client.put(
            reverse('Categoria_update'), {'nombre': 'Ficción'}, format='json')

        self.assert_envelope_error(response)


class LibrosErroresTests(BaseAPITest):
    """Errores del recurso Libros."""

    def setUp(self):
        self.categoria = self.crear_categoria(nombre='Ficción')

    def test_isbn_duplicado(self):
        self.crear_libro(titulo='Dune', isbn='978-1', categoria=self.categoria)

        response = self.client.post(
            reverse('Libro_add'),
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
            reverse('Libro_add'),
            {'titulo': 'Dune', 'autor': 'Frank Herbert', 'isbn': '978-2',
             'cantidad': 0, 'id_categoria': self.categoria.id_categoria},
            format='json',
        )

        self.assert_envelope_error(response)

    def test_cantidad_negativa(self):
        response = self.client.post(
            reverse('Libro_add'),
            {'titulo': 'Dune', 'autor': 'Frank Herbert', 'isbn': '978-3',
             'cantidad': -3, 'id_categoria': self.categoria.id_categoria},
            format='json',
        )

        self.assert_envelope_error(response)

    def test_crear_sin_campos_requeridos(self):
        response = self.client.post(
            reverse('Libro_add'),
            {'titulo': 'Dune', 'id_categoria': self.categoria.id_categoria},
            format='json',
        )

        self.assert_envelope_error(response)

    def test_view_inexistente(self):
        url = f"{reverse('Libro_view')}?id_libro=9999"
        response = self.client.get(url)

        self.assert_envelope_error(response, HTTP_404_NOT_FOUND)

    def test_update_inexistente(self):
        response = self.client.put(
            reverse('Libro_update'),
            {'id_libro': 9999, 'titulo': 'Dune', 'autor': 'A',
             'id_categoria': self.categoria.id_categoria},
            format='json',
        )

        self.assert_envelope_error(response, HTTP_404_NOT_FOUND)

    def test_delete_inexistente(self):
        url = f"{reverse('Libro_delete')}?id_libro=9999"
        response = self.client.delete(url)

        self.assert_envelope_error(response, HTTP_404_NOT_FOUND)


class UsuariosErroresTests(BaseAPITest):
    """Errores del recurso Usuarios, incluyendo el manejo de contraseñas."""

    CONTRASENA_PLANA = 'clave-super-secreta-42'

    def test_correo_duplicado(self):
        self.crear_usuario(correo='juan@test.com')

        response = self.client.post(
            reverse('Usuario_add'),
            {'nombre': 'Juan', 'apellido': 'Perez', 'correo': 'juan@test.com',
             'contrasena': 'otra-clave-1'},
            format='json',
        )

        self.assert_envelope_error(response)
        # El mensaje es claro (duplicado), no el genérico "Complete los campos vacios".
        self.assertEqual(response.data['Mensaje']['correo'][0],
                         'Ya existe un usuario con ese correo')

    def test_crear_sin_contrasena(self):
        response = self.client.post(
            reverse('Usuario_add'),
            {'nombre': 'Juan', 'apellido': 'Perez', 'correo': 'juan@test.com'},
            format='json',
        )

        self.assert_envelope_error(response)

    def test_view_inexistente(self):
        url = f"{reverse('Usuario_view')}?id_usuario=9999"
        response = self.client.get(url)

        self.assert_envelope_error(response, HTTP_404_NOT_FOUND)

    def test_update_inexistente(self):
        response = self.client.put(
            reverse('Usuario_update'),
            {'id_usuario': 9999, 'nombre': 'Juan', 'apellido': 'Perez',
             'correo': 'juan@test.com', 'contrasena': 'clave-1'},
            format='json',
        )

        self.assert_envelope_error(response, HTTP_404_NOT_FOUND)

    def test_delete_inexistente(self):
        url = f"{reverse('Usuario_delete')}?id_usuario=9999"
        response = self.client.delete(url)

        self.assert_envelope_error(response, HTTP_404_NOT_FOUND)

    def test_contrasena_no_aparece_al_crear(self):
        response = self.client.post(
            reverse('Usuario_add'),
            {'nombre': 'Juan', 'apellido': 'Perez', 'correo': 'juan@test.com',
             'contrasena': self.CONTRASENA_PLANA},
            format='json',
        )

        self.assert_envelope_exitosa(response, HTTP_201_CREATED)
        self.assertNotIn('contrasena', response.data['datos'])
        self.assertNotIn(self.CONTRASENA_PLANA, str(response.data))

    def test_contrasena_no_aparece_en_lista_ni_view(self):
        usuario = self.crear_usuario(correo='juan@test.com',
                                     contrasena=self.CONTRASENA_PLANA)

        response_lista = self.client.get(reverse('usuarios_list'))
        self.assert_envelope_exitosa(response_lista)
        self.assertNotIn(self.CONTRASENA_PLANA, str(response_lista.data))
        for item in response_lista.data['datos']:
            self.assertNotIn('contrasena', item)

        url = f"{reverse('Usuario_view')}?id_usuario={usuario.id_usuario}"
        response_view = self.client.get(url)
        self.assert_envelope_exitosa(response_view)
        self.assertNotIn(self.CONTRASENA_PLANA, str(response_view.data))
        self.assertNotIn('contrasena', response_view.data['datos'][0])

    def test_contrasena_almacenada_hasheada(self):
        usuario = self.crear_usuario(correo='juan@test.com',
                                     contrasena=self.CONTRASENA_PLANA)

        self.assertNotEqual(usuario.contrasena, self.CONTRASENA_PLANA)
        self.assertTrue(usuario.contrasena.startswith('pbkdf2_'))
        self.assertTrue(usuario.check_contrasena(self.CONTRASENA_PLANA))


class PrestamosErroresTests(BaseAPITest):
    """Errores del recurso Prestamos."""

    def setUp(self):
        self.usuario = self.crear_usuario(correo='juan@test.com')
        self.libro = self.crear_libro(titulo='Dune', isbn='978-1', cantidad=5)

    def test_fecha_devolucion_anterior_a_fecha_prestamo(self):
        hoy = date.today()
        response = self.client.post(
            reverse('Prestamo_add'),
            {'id_usuario': self.usuario.id_usuario,
             'id_libro': self.libro.id_libro,
             'fecha_prestamo': hoy.isoformat(),
             'fecha_devolucion': (hoy - timedelta(days=1)).isoformat()},
            format='json',
        )

        self.assert_envelope_error(response)

    def test_view_inexistente(self):
        url = f"{reverse('Prestamo_view')}?id_prestamo=9999"
        response = self.client.get(url)

        self.assert_envelope_error(response, HTTP_404_NOT_FOUND)

    def test_update_inexistente(self):
        hoy = date.today()
        response = self.client.put(
            reverse('Prestamo_update'),
            {'id_prestamo': 9999, 'id_usuario': self.usuario.id_usuario,
             'id_libro': self.libro.id_libro,
             'fecha_prestamo': hoy.isoformat()},
            format='json',
        )

        self.assert_envelope_error(response, HTTP_404_NOT_FOUND)

    def test_delete_inexistente(self):
        url = f"{reverse('Prestamo_delete')}?id_prestamo=9999"
        response = self.client.delete(url)

        self.assert_envelope_error(response, HTTP_404_NOT_FOUND)

    def test_crear_sin_campos_requeridos(self):
        response = self.client.post(
            reverse('Prestamo_add'),
            {'id_usuario': self.usuario.id_usuario},
            format='json',
        )

        self.assert_envelope_error(response)

    def test_update_fecha_devolucion_invalida(self):
        prestamo = self.crear_prestamo(usuario=self.usuario, libro=self.libro)
        hoy = date.today()
        response = self.client.put(
            reverse('Prestamo_update'),
            {'id_prestamo': prestamo.id_prestamo,
             'id_usuario': self.usuario.id_usuario,
             'id_libro': self.libro.id_libro,
             'fecha_prestamo': hoy.isoformat(),
             'fecha_devolucion': (hoy - timedelta(days=2)).isoformat()},
            format='json',
        )

        self.assert_envelope_error(response)
        # El préstamo no debe haber cambiado.
        prestamo.refresh_from_db()
        self.assertEqual(prestamo.estado, Prestamo.ESTADO_PRESTADO)
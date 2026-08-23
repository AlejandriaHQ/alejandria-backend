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
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
)

from biblioteca.models import Categoria, Prestamo, Usuario
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
        # RN-07 / RF-10: una categoría con libros asociados NO se elimina
        # físicamente (la FK de Libro usa PROTECT); se desactiva mediante
        # eliminación lógica para conservar los libros que la referencian.
        categoria = self.crear_categoria(nombre='Ficción')
        self.crear_libro(titulo='Dune', isbn='978-1', categoria=categoria)

        response = self.client.delete(
            reverse('categoria-detail', args=[categoria.id_categoria]))

        self.assert_envelope_exitosa(response)
        categoria.refresh_from_db()
        self.assertFalse(categoria.activo)
        # La categoría sigue existiendo en la BD (no se borró físicamente).
        self.assertTrue(Categoria.objects.filter(pk=categoria.pk).exists())


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

    def test_cantidad_excede_maximo(self):
        # F10 pentest: por encima del tope superior (10000) se rechaza con 400.
        response = self.client.post(
            reverse('libro-list'),
            {'titulo': 'Dune', 'autor': 'Frank Herbert', 'isbn': '978-9',
             'cantidad': 10001, 'id_categoria': self.categoria.id_categoria},
            format='json',
        )

        self.assert_envelope_error(response)
        self.assertEqual(response.data['Mensaje']['cantidad'][0],
                         'Ensure this value is less than or equal to 10000.')

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

    def test_pagina_no_numerica(self):
        # F16 pentest: page no numérico se rechaza con 400 (antes se
        # degradaba silenciosamente a página 1).
        url = f"{reverse('libro-paginar')}?page=abc"
        response = self.client.get(url)

        self.assert_envelope_error(response)


class UsuariosErroresTests(BaseAPITest):
    """Errores y validaciones del recurso Usuarios.

    Incluye: duplicados (email/cedula), formato de cédula, longitud de
    contraseña, manejo de contraseñas (write_only + hash) y la protección de
    escritura por rol (solo admin/staff).
    """

    PASSWORD_PLANA = 'clave-super-secreta-42'
    MENSAJE_GENERICO = 'No se pudo completar la operación. Revise los datos enviados.'
    MENSAJE_CEDULA_FORMATO = 'La cédula debe tener el formato 000-0000000-0'
    MENSAJE_PASSWORD_CORTA = 'La contraseña debe tener al menos 6 caracteres'

    def payload_usuario(self, **overrides):
        payload = {
            'first_name': 'Juan',
            'last_name': 'Perez',
            'email': 'juan@test.com',
            'password': self.PASSWORD_PLANA,
            'phone': '809-555-1234',
            'cedula': '001-1234567-8',
            'address': 'Calle 5',
            'role': 'user',
        }
        payload.update(overrides)
        return payload

    def test_correo_duplicado(self):
        self.crear_usuario(email='juan@test.com')

        response = self.client.post(
            reverse('usuario-list'),
            self.payload_usuario(),
            format='json',
        )

        self.assert_envelope_error(response)
        # F09 pentest: el mensaje es GENÉRICO a propósito — no confirma que el
        # correo ya existe (evita enumerar cuentas).
        self.assertEqual(response.data['Mensaje']['email'][0],
                         self.MENSAJE_GENERICO)

    def test_cedula_duplicada(self):
        self.crear_usuario(cedula='001-1234567-8')

        response = self.client.post(
            reverse('usuario-list'),
            self.payload_usuario(email='otro@test.com'),
            format='json',
        )

        self.assert_envelope_error(response)
        # F09: mismo mensaje genérico que el correo.
        self.assertEqual(response.data['Mensaje']['cedula'][0],
                         self.MENSAJE_GENERICO)

    def test_cedula_formato_invalido(self):
        response = self.client.post(
            reverse('usuario-list'),
            self.payload_usuario(cedula='12345678'),
            format='json',
        )

        self.assert_envelope_error(response)
        self.assertEqual(response.data['Mensaje']['cedula'][0],
                         self.MENSAJE_CEDULA_FORMATO)

    def test_crear_sin_password(self):
        payload = self.payload_usuario()
        payload.pop('password')

        response = self.client.post(
            reverse('usuario-list'),
            payload,
            format='json',
        )

        self.assert_envelope_error(response)
        self.assertIn('Complete la casilla password', response.data['Mensaje'])

    def test_crear_sin_cedula(self):
        payload = self.payload_usuario()
        payload.pop('cedula')

        response = self.client.post(
            reverse('usuario-list'),
            payload,
            format='json',
        )

        self.assert_envelope_error(response)
        self.assertIn('Complete la casilla cedula', response.data['Mensaje'])

    def test_crear_sin_role(self):
        payload = self.payload_usuario()
        payload.pop('role')

        response = self.client.post(
            reverse('usuario-list'),
            payload,
            format='json',
        )

        self.assert_envelope_error(response)
        self.assertIn('Complete la casilla role', response.data['Mensaje'])

    def test_password_corta(self):
        response = self.client.post(
            reverse('usuario-list'),
            self.payload_usuario(password='12345'),
            format='json',
        )

        self.assert_envelope_error(response)
        self.assertEqual(response.data['Mensaje']['password'][0],
                         self.MENSAJE_PASSWORD_CORTA)

    def test_view_inexistente(self):
        response = self.client.get(reverse('usuario-detail', args=[9999]))

        self.assert_envelope_error(response, HTTP_404_NOT_FOUND)

    def test_update_inexistente(self):
        response = self.client.put(
            reverse('usuario-detail', args=[9999]),
            self.payload_usuario(),
            format='json',
        )

        self.assert_envelope_error(response, HTTP_404_NOT_FOUND)

    def test_delete_inexistente(self):
        response = self.client.delete(reverse('usuario-detail', args=[9999]))

        self.assert_envelope_error(response, HTTP_404_NOT_FOUND)

    def test_password_no_aparece_al_crear(self):
        response = self.client.post(
            reverse('usuario-list'),
            self.payload_usuario(),
            format='json',
        )

        self.assert_envelope_exitosa(response, HTTP_201_CREATED)
        self.assertNotIn('password', response.data['datos'])
        self.assertNotIn(self.PASSWORD_PLANA, str(response.data))

    def test_password_no_aparece_en_lista_ni_view(self):
        usuario = self.crear_usuario(email='juan@test.com',
                                     password=self.PASSWORD_PLANA)

        response_lista = self.client.get(reverse('usuario-list'))
        self.assert_envelope_exitosa(response_lista)
        self.assertNotIn(self.PASSWORD_PLANA, str(response_lista.data))
        for item in response_lista.data['datos']:
            self.assertNotIn('password', item)

        response_view = self.client.get(
            reverse('usuario-detail', args=[usuario.id]))
        self.assert_envelope_exitosa(response_view)
        self.assertNotIn(self.PASSWORD_PLANA, str(response_view.data))
        self.assertNotIn('password', response_view.data['datos'])

    def test_password_almacenada_hasheada(self):
        usuario = self.crear_usuario(email='juan@test.com',
                                     password=self.PASSWORD_PLANA)

        self.assertNotEqual(usuario.password, self.PASSWORD_PLANA)
        self.assertTrue(usuario.password.startswith('pbkdf2_'))
        self.assertTrue(usuario.check_password(self.PASSWORD_PLANA))


class UsuariosProteccionRolesTests(BaseAPITest):
    """Solo un admin/staff puede crear, actualizar o eliminar usuarios.

    Un usuario común (role='user') debe recibir 403 incluso intentando
    asignar role='admin' en el payload (la comprobación ocurre antes de que
    el payload llegue al serializer).
    """

    def setUp(self):
        super().setUp()
        self.usuario_comun = Usuario(
            first_name='Maria', last_name='Gomez', email='maria@test.com',
            role='user',
        )
        self.usuario_comun.set_password('clave-comun-123')
        self.usuario_comun.save()

    def payload(self, **overrides):
        payload = {
            'first_name': 'Juan',
            'last_name': 'Perez',
            'email': 'juan@test.com',
            'password': 'clave-secreta-1',
            'phone': '809-555-1234',
            'cedula': '001-1234567-8',
            'address': 'Calle 5',
            'role': 'user',
        }
        payload.update(overrides)
        return payload

    def test_usuario_comun_no_puede_crear(self):
        self.autenticar_como(self.usuario_comun)

        response = self.client.post(
            reverse('usuario-list'),
            self.payload(),
            format='json',
        )

        self.assert_envelope_error(response, HTTP_403_FORBIDDEN)
        self.assertEqual(Usuario.objects.count(), 1)  # solo el usuario_comun

    def test_usuario_comun_no_puede_crear_con_role_admin(self):
        # El intento más sensible: un no-admin intenta crearse como admin.
        self.autenticar_como(self.usuario_comun)

        response = self.client.post(
            reverse('usuario-list'),
            self.payload(email='yo-admin@test.com', role='admin'),
            format='json',
        )

        self.assert_envelope_error(response, HTTP_403_FORBIDDEN)
        self.assertEqual(Usuario.objects.filter(role='admin').count(), 0)

    def test_usuario_comun_no_puede_actualizar(self):
        self.autenticar_como(self.usuario_comun)

        response = self.client.put(
            reverse('usuario-detail', args=[self.usuario_comun.id]),
            self.payload(email='maria@test.com'),
            format='json',
        )

        self.assert_envelope_error(response, HTTP_403_FORBIDDEN)

    def test_usuario_comun_no_puede_eliminar(self):
        self.autenticar_como(self.usuario_comun)

        response = self.client.delete(
            reverse('usuario-detail', args=[self.usuario_comun.id]))

        self.assert_envelope_error(response, HTTP_403_FORBIDDEN)
        self.assertEqual(Usuario.objects.count(), 1)

    def test_usuario_comun_si_puede_leer(self):
        # La lectura queda abierta a cualquier usuario autenticado.
        self.autenticar_como(self.usuario_comun)

        response = self.client.get(reverse('usuario-list'))

        self.assert_envelope_exitosa(response)
        self.assertEqual(len(response.data['datos']), 1)


class PrestamosErroresTests(BaseAPITest):
    """Errores del recurso Prestamos."""

    def setUp(self):
        super().setUp()
        self.usuario = self.crear_usuario(email='juan@test.com')
        self.libro = self.crear_libro(titulo='Dune', isbn='978-1', cantidad=5)

    def test_fecha_devolucion_anterior_a_fecha_prestamo(self):
        hoy = date.today()
        response = self.client.post(
            reverse('prestamo-list'),
            {'id_usuario': self.usuario.id,
             'id_libro': self.libro.id_libro,
             'fecha_prestamo': hoy.isoformat(),
             'fecha_devolucion': (hoy - timedelta(days=1)).isoformat()},
            format='json',
        )

        self.assert_envelope_error(response)

    def test_fecha_prestamo_fuera_de_rango_rechazada(self):
        # F12 pentest: una fecha de préstamo muy retroactiva (hace más de un
        # año) o demasiado futura se rechaza con 400 y un mensaje claro.
        hoy = date.today()
        for dias in (-400, 400):
            response = self.client.post(
                reverse('prestamo-list'),
                {'id_usuario': self.usuario.id,
                 'id_libro': self.libro.id_libro,
                 'fecha_prestamo': (hoy + timedelta(days=dias)).isoformat()},
                format='json',
            )

            self.assert_envelope_error(response)
            self.assertIn('fecha_prestamo', response.data['Mensaje'])

    def test_view_inexistente(self):
        response = self.client.get(reverse('prestamo-detail', args=[9999]))

        self.assert_envelope_error(response, HTTP_404_NOT_FOUND)

    def test_update_inexistente(self):
        hoy = date.today()
        response = self.client.put(
            reverse('prestamo-detail', args=[9999]),
            {'id_usuario': self.usuario.id,
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
            {'id_usuario': self.usuario.id},
            format='json',
        )

        self.assert_envelope_error(response)

    def test_update_fecha_devolucion_invalida(self):
        prestamo = self.crear_prestamo(usuario=self.usuario, libro=self.libro)
        hoy = date.today()
        response = self.client.put(
            reverse('prestamo-detail', args=[prestamo.id_prestamo]),
            {'id_usuario': self.usuario.id,
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
        # Se limpia la autenticación que setUp dejó en el cliente
        # (force_authenticate) para simular un request anónimo.
        self.client.force_authenticate(user=None)

        response = self.client.get(reverse('categoria-list'))

        self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED)

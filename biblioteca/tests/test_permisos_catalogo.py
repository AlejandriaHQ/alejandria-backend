"""Cobertura de la protección por rol en el Catálogo (Fase 4 / RN-05 / RFC-25).

Replica la guarda de Préstamos y Reportes: solo un usuario con role='admin'
(o is_staff) puede crear/editar/eliminar libros y categorías. La lectura
(list/retrieve/paginar) queda abierta a cualquier usuario autenticado.

Se verifica con ``biblioteca.tests.helpers.BaseAPITest``:
- el admin (por defecto en setUp) escribe con éxito;
- un usuario común (role='user') recibe 403 y NO muta la BD en create/destroy;
- la lectura de catálogo sigue permitida a cualquier autenticado.
"""
from django.urls import reverse
from rest_framework.status import HTTP_403_FORBIDDEN

from biblioteca.models import Categoria, Libro
from biblioteca.tests.helpers import BaseAPITest


class PermisosCatalogoLibrosTests(BaseAPITest):
    """Protección de escritura sobre Libros (RN-05 / RFC-25)."""

    def setUp(self):
        super().setUp()
        self.usuario = self.crear_usuario(email='juan@test.com')
        self.admin = self.crear_usuario(email='admin@test.com', role='admin')
        self.categoria = self.crear_categoria()

    def _payload_libro(self, titulo="Libro protegido", isbn="9783161484100"):
        return {
            'titulo': titulo,
            'autor': 'Autor de prueba',
            'isbn': isbn,
            'cantidad': 5,
            'id_categoria': self.categoria.id_categoria,
        }

    def test_admin_puede_crear_libro(self):
        self.autenticar_como(self.admin)
        response = self.client.post(
            reverse('libro-list'), self._payload_libro(), format='json')

        self.assert_envelope_exitosa(response, 201)
        self.assertEqual(Libro.objects.count(), 1)

    def test_usuario_normal_no_puede_crear_libro(self):
        count_antes = Libro.objects.count()
        self.autenticar_como(self.usuario)
        response = self.client.post(
            reverse('libro-list'), self._payload_libro(), format='json')

        self.assert_envelope_error(response, HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['Mensaje'],
                         'No tiene permisos para realizar esta acción')
        # El libro NO se creó pese al 403.
        self.assertEqual(Libro.objects.count(), count_antes)

    def test_usuario_normal_no_puede_eliminar_libro(self):
        # El libro se crea como admin (escritura permitida).
        self.autenticar_como(self.admin)
        creacion = self.client.post(
            reverse('libro-list'), self._payload_libro(), format='json')
        libro_id = creacion.data['datos']['id_libro']
        self.assertEqual(Libro.objects.count(), 1)

        # Un usuario común no debería poder borrarlo.
        self.autenticar_como(self.usuario)
        response = self.client.delete(reverse('libro-detail', args=[libro_id]))

        self.assert_envelope_error(response, HTTP_403_FORBIDDEN)
        # El libro sigue existiendo.
        self.assertEqual(Libro.objects.filter(pk=libro_id).count(), 1)

    def test_usuario_normal_puede_listar_libros(self):
        # La lectura queda abierta a cualquier usuario autenticado.
        self.crear_libro(titulo='Libro leíble')
        self.autenticar_como(self.usuario)

        response = self.client.get(reverse('libro-list'))

        self.assert_envelope_exitosa(response)
        self.assertEqual(len(response.data['datos']), 1)


class PermisosCatalogoCategoriasTests(BaseAPITest):
    """Protección de escritura sobre Categorías (RN-05 / RFC-25)."""

    def setUp(self):
        super().setUp()
        self.usuario = self.crear_usuario(email='juan@test.com')
        self.admin = self.crear_usuario(email='admin@test.com', role='admin')

    def _payload_categoria(self, nombre="Categoría protegida"):
        return {'nombre': nombre, 'descripcion': 'Descripción de prueba'}

    def test_admin_puede_crear_categoria(self):
        self.autenticar_como(self.admin)
        response = self.client.post(
            reverse('categoria-list'), self._payload_categoria(), format='json')

        self.assert_envelope_exitosa(response, 201)
        self.assertEqual(Categoria.objects.count(), 1)

    def test_usuario_normal_no_puede_crear_categoria(self):
        count_antes = Categoria.objects.count()
        self.autenticar_como(self.usuario)
        response = self.client.post(
            reverse('categoria-list'), self._payload_categoria(), format='json')

        self.assert_envelope_error(response, HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['Mensaje'],
                         'No tiene permisos para realizar esta acción')
        # La categoría NO se creó pese al 403.
        self.assertEqual(Categoria.objects.count(), count_antes)

    def test_usuario_normal_puede_listar_categorias(self):
        # La lectura queda abierta a cualquier usuario autenticado.
        self.crear_categoria(nombre='Categoría leíble')
        self.autenticar_como(self.usuario)

        response = self.client.get(reverse('categoria-list'))

        self.assert_envelope_exitosa(response)
        self.assertEqual(len(response.data['datos']), 1)

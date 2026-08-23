"""Cobertura CRUD básico de las cuatro entidades: Categorias, Libros,
Usuarios y Prestamos.

Verifica listar, crear, ver por id, actualizar, eliminar y paginación,
comprobando el envelope JSON y los status codes de cada endpoint REST.
"""
from datetime import date, timedelta

from django.urls import reverse
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED

from biblioteca.models import Categoria, Libro, Prestamo, Usuario
from biblioteca.tests.helpers import BaseAPITest

PAGE_SIZE = 10


class CategoriasCRUDTests(BaseAPITest):
    """CRUD y paginación del recurso Categorias."""

    def test_listar_categorias_vacia(self):
        response = self.client.get(reverse('categoria-list'))

        self.assert_envelope_exitosa(response)
        self.assertEqual(response.data['datos'], [])

    def test_listar_categorias(self):
        self.crear_categoria(nombre='Ficción')
        self.crear_categoria(nombre='Terror')

        response = self.client.get(reverse('categoria-list'))

        self.assert_envelope_exitosa(response)
        self.assertEqual(len(response.data['datos']), 2)
        nombres = {item['nombre'] for item in response.data['datos']}
        self.assertEqual(nombres, {'Ficción', 'Terror'})

    def test_crear_categoria(self):
        response = self.client.post(
            reverse('categoria-list'),
            {'nombre': 'Ciencia Ficción', 'descripcion': 'Novelas de ciencia ficción'},
            format='json',
        )

        self.assert_envelope_exitosa(response, HTTP_201_CREATED)
        self.assertEqual(Categoria.objects.count(), 1)
        categoria = Categoria.objects.get()
        self.assertEqual(response.data['datos']['id_categoria'], categoria.id_categoria)
        self.assertEqual(response.data['datos']['nombre'], 'Ciencia Ficción')
        self.assertEqual(response.data['datos']['descripcion'], 'Novelas de ciencia ficción')

    def test_ver_categoria_por_id(self):
        categoria = self.crear_categoria(nombre='Ficción')

        response = self.client.get(
            reverse('categoria-detail', args=[categoria.id_categoria]))

        self.assert_envelope_exitosa(response)
        self.assertEqual(response.data['datos']['id_categoria'], categoria.id_categoria)
        self.assertEqual(response.data['datos']['nombre'], 'Ficción')

    def test_actualizar_categoria(self):
        categoria = self.crear_categoria(nombre='Ficción', descripcion='Antes')

        response = self.client.put(
            reverse('categoria-detail', args=[categoria.id_categoria]),
            {'nombre': 'Terror', 'descripcion': 'Después'},
            format='json',
        )

        self.assert_envelope_exitosa(response)
        categoria.refresh_from_db()
        self.assertEqual(categoria.nombre, 'Terror')
        self.assertEqual(categoria.descripcion, 'Después')

    def test_eliminar_categoria(self):
        categoria = self.crear_categoria()

        response = self.client.delete(
            reverse('categoria-detail', args=[categoria.id_categoria]))

        self.assert_envelope_exitosa(response)
        self.assertEqual(Categoria.objects.count(), 0)

    def test_paginador_categorias(self):
        for i in range(12):
            self.crear_categoria(nombre=f'Categoría {i}')

        pagina1 = self.client.get(f"{reverse('categoria-paginar')}?page=1")
        self.assert_envelope_exitosa(pagina1)
        self.assertEqual(len(pagina1.data['datos']), PAGE_SIZE)
        self.assertFalse(pagina1.data['previous'])
        self.assertTrue(pagina1.data['next'])
        self.assertEqual(pagina1.data['maxPages'], 2)
        self.assertEqual(pagina1.data['currentpage'], 1)

        pagina2 = self.client.get(f"{reverse('categoria-paginar')}?page=2")
        self.assert_envelope_exitosa(pagina2)
        self.assertEqual(len(pagina2.data['datos']), 2)
        self.assertTrue(pagina2.data['previous'])
        self.assertFalse(pagina2.data['next'])

    def test_paginador_categorias_con_filtro(self):
        self.crear_categoria(nombre='Ficción', descripcion='Ciencia')
        self.crear_categoria(nombre='Terror', descripcion='Suspenso')

        url = f"{reverse('categoria-paginar')}?page=1&filter=fic"
        response = self.client.get(url)

        self.assert_envelope_exitosa(response)
        self.assertEqual(len(response.data['datos']), 1)
        self.assertEqual(response.data['datos'][0]['nombre'], 'Ficción')


class LibrosCRUDTests(BaseAPITest):
    """CRUD y paginación del recurso Libros."""

    def setUp(self):
        super().setUp()
        self.categoria = self.crear_categoria(nombre='Ficción')

    def test_listar_libros_vacia(self):
        response = self.client.get(reverse('libro-list'))

        self.assert_envelope_exitosa(response)
        self.assertEqual(response.data['datos'], [])

    def test_listar_libros(self):
        self.crear_libro(titulo='Dune', autor='Frank Herbert', isbn='978-1',
                         categoria=self.categoria)
        self.crear_libro(titulo='Neuromante', autor='William Gibson', isbn='978-2',
                         categoria=self.categoria)

        response = self.client.get(reverse('libro-list'))

        self.assert_envelope_exitosa(response)
        self.assertEqual(len(response.data['datos']), 2)
        titulos = {item['titulo'] for item in response.data['datos']}
        self.assertEqual(titulos, {'Dune', 'Neuromante'})

    def test_crear_libro(self):
        response = self.client.post(
            reverse('libro-list'),
            {'titulo': 'Dune', 'autor': 'Frank Herbert', 'isbn': '9780306406157',
             'cantidad': 4, 'id_categoria': self.categoria.id_categoria},
            format='json',
        )

        self.assert_envelope_exitosa(response, HTTP_201_CREATED)
        self.assertEqual(Libro.objects.count(), 1)
        libro = Libro.objects.get()
        self.assertEqual(response.data['datos']['id_libro'], libro.id_libro)
        self.assertEqual(response.data['datos']['titulo'], 'Dune')
        self.assertEqual(response.data['datos']['cantidad'], 4)

    def test_crear_libro_sin_cantidad_usa_default(self):
        response = self.client.post(
            reverse('libro-list'),
            {'titulo': 'Dune', 'autor': 'Frank Herbert', 'isbn': '9783161484100',
             'id_categoria': self.categoria.id_categoria},
            format='json',
        )

        self.assert_envelope_exitosa(response, HTTP_201_CREATED)
        self.assertEqual(response.data['datos']['cantidad'], 1)

    def test_ver_libro_por_id(self):
        libro = self.crear_libro(titulo='Dune', isbn='978-5', categoria=self.categoria)

        response = self.client.get(reverse('libro-detail', args=[libro.id_libro]))

        self.assert_envelope_exitosa(response)
        self.assertEqual(response.data['datos']['id_libro'], libro.id_libro)
        self.assertEqual(response.data['datos']['titulo'], 'Dune')

    def test_actualizar_libro(self):
        libro = self.crear_libro(titulo='Dune', autor='Frank Herbert',
                                 isbn='978-6', cantidad=4, categoria=self.categoria)

        response = self.client.put(
            reverse('libro-detail', args=[libro.id_libro]),
            {'titulo': 'Dune 2', 'autor': 'Frank Herbert',
             'isbn': '9780132350884', 'cantidad': 7, 'id_categoria': self.categoria.id_categoria},
            format='json',
        )

        self.assert_envelope_exitosa(response)
        libro.refresh_from_db()
        self.assertEqual(libro.titulo, 'Dune 2')
        self.assertEqual(libro.cantidad, 7)

    def test_eliminar_libro(self):
        libro = self.crear_libro(isbn='978-7', categoria=self.categoria)

        response = self.client.delete(reverse('libro-detail', args=[libro.id_libro]))

        self.assert_envelope_exitosa(response)
        self.assertEqual(Libro.objects.count(), 0)

    def test_paginador_libros(self):
        for i in range(12):
            self.crear_libro(titulo=f'Libro {i}', isbn=f'978-{i:04d}',
                             categoria=self.categoria)

        pagina1 = self.client.get(f"{reverse('libro-paginar')}?page=1")
        self.assert_envelope_exitosa(pagina1)
        self.assertEqual(len(pagina1.data['datos']), PAGE_SIZE)
        self.assertFalse(pagina1.data['previous'])
        self.assertTrue(pagina1.data['next'])
        self.assertEqual(pagina1.data['maxPages'], 2)

        pagina2 = self.client.get(f"{reverse('libro-paginar')}?page=2")
        self.assert_envelope_exitosa(pagina2)
        self.assertEqual(len(pagina2.data['datos']), 2)
        self.assertTrue(pagina2.data['previous'])
        self.assertFalse(pagina2.data['next'])


class UsuariosCRUDTests(BaseAPITest):
    """CRUD y paginación del recurso Usuarios (modelo AbstractUser)."""

    # Payload mínimo válido del panel admin.
    def payload_usuario(self, **overrides):
        payload = {
            'first_name': 'Juan',
            'last_name': 'Perez',
            'email': 'juan@test.com',
            'password': 'clave-secreta-1',
            'phone': '809-555-1234',
            'cedula': '001-1234567-8',
            'address': 'Calle 5, Santo Domingo',
            'role': 'user',
        }
        payload.update(overrides)
        return payload

    def test_listar_usuarios_vacia(self):
        response = self.client.get(reverse('usuario-list'))

        self.assert_envelope_exitosa(response)
        self.assertEqual(response.data['datos'], [])

    def test_listar_usuarios(self):
        self.crear_usuario(first_name='Juan', last_name='Perez', email='juan@test.com')
        self.crear_usuario(first_name='Ana', last_name='Lopez', email='ana@test.com')

        response = self.client.get(reverse('usuario-list'))

        self.assert_envelope_exitosa(response)
        self.assertEqual(len(response.data['datos']), 2)
        correos = {item['email'] for item in response.data['datos']}
        self.assertEqual(correos, {'juan@test.com', 'ana@test.com'})

    def test_crear_usuario(self):
        response = self.client.post(
            reverse('usuario-list'),
            self.payload_usuario(),
            format='json',
        )

        self.assert_envelope_exitosa(response, HTTP_201_CREATED)
        self.assertEqual(Usuario.objects.count(), 1)
        usuario = Usuario.objects.get()
        self.assertEqual(response.data['datos']['id'], usuario.id)
        self.assertEqual(response.data['datos']['email'], 'juan@test.com')
        self.assertNotIn('password', response.data['datos'])

    def test_crear_usuario_genera_identifier_mem(self):
        response = self.client.post(
            reverse('usuario-list'),
            self.payload_usuario(role='user'),
            format='json',
        )

        self.assert_envelope_exitosa(response, HTTP_201_CREATED)
        identifier = response.data['datos']['identifier']
        self.assertTrue(identifier.startswith('MEM-'))
        self.assertEqual(Usuario.objects.get().identifier, identifier)

    def test_crear_admin_genera_identifier_adm(self):
        response = self.client.post(
            reverse('usuario-list'),
            self.payload_usuario(email='admin1@test.com', role='admin'),
            format='json',
        )

        self.assert_envelope_exitosa(response, HTTP_201_CREATED)
        self.assertTrue(response.data['datos']['identifier'].startswith('ADM-'))
        usuario = Usuario.objects.get(email='admin1@test.com')
        self.assertEqual(usuario.role, 'admin')
        self.assertTrue(usuario.is_staff)

    def test_ver_usuario_por_id(self):
        usuario = self.crear_usuario(email='juan@test.com')

        response = self.client.get(reverse('usuario-detail', args=[usuario.id]))

        self.assert_envelope_exitosa(response)
        self.assertEqual(response.data['datos']['id'], usuario.id)
        self.assertEqual(response.data['datos']['email'], 'juan@test.com')

    def test_actualizar_usuario_con_password(self):
        usuario = self.crear_usuario(first_name='Juan', last_name='Perez',
                                     email='juan@test.com')

        response = self.client.put(
            reverse('usuario-detail', args=[usuario.id]),
            self.payload_usuario(first_name='Juan Carlos', phone='809-555-9999'),
            format='json',
        )

        self.assert_envelope_exitosa(response)
        usuario.refresh_from_db()
        self.assertEqual(usuario.first_name, 'Juan Carlos')
        self.assertEqual(usuario.phone, '809-555-9999')
        self.assertTrue(usuario.check_password('clave-secreta-1'))

    def test_actualizar_usuario_sin_password_conserva_clave(self):
        usuario = self.crear_usuario(first_name='Juan', last_name='Perez',
                                     email='juan@test.com',
                                     password='clave-original')

        payload = self.payload_usuario(first_name='Juan Carlos',
                                       phone='809-555-0000')
        payload.pop('password')  # el PUT no reenvía la contraseña

        response = self.client.put(
            reverse('usuario-detail', args=[usuario.id]),
            payload,
            format='json',
        )

        self.assert_envelope_exitosa(response)
        usuario.refresh_from_db()
        self.assertEqual(usuario.first_name, 'Juan Carlos')
        self.assertEqual(usuario.phone, '809-555-0000')
        # La contraseña antigua sigue siendo válida: no se pisó el hash.
        self.assertTrue(usuario.check_password('clave-original'))

    def test_eliminar_usuario(self):
        usuario = self.crear_usuario(email='juan@test.com')

        response = self.client.delete(reverse('usuario-detail', args=[usuario.id]))

        self.assert_envelope_exitosa(response)
        self.assertEqual(Usuario.objects.count(), 0)

    def test_paginador_usuarios(self):
        for i in range(12):
            self.crear_usuario(first_name=f'Usuario {i}', last_name='Test',
                               email=f'usuario{i}@test.com')

        pagina1 = self.client.get(f"{reverse('usuario-paginar')}?page=1")
        self.assert_envelope_exitosa(pagina1)
        self.assertEqual(len(pagina1.data['datos']), PAGE_SIZE)
        self.assertFalse(pagina1.data['previous'])
        self.assertTrue(pagina1.data['next'])
        self.assertEqual(pagina1.data['maxPages'], 2)

        pagina2 = self.client.get(f"{reverse('usuario-paginar')}?page=2")
        self.assert_envelope_exitosa(pagina2)
        self.assertEqual(len(pagina2.data['datos']), 2)
        self.assertTrue(pagina2.data['previous'])
        self.assertFalse(pagina2.data['next'])


class PrestamosCRUDTests(BaseAPITest):
    """CRUD y paginación del recurso Prestamos."""

    def setUp(self):
        super().setUp()
        self.usuario = self.crear_usuario(email='juan@test.com')
        self.libro = self.crear_libro(titulo='Dune', isbn='978-11', cantidad=5)

    def test_listar_prestamos_vacia(self):
        response = self.client.get(reverse('prestamo-list'))

        self.assert_envelope_exitosa(response)
        self.assertEqual(response.data['datos'], [])

    def test_listar_prestamos(self):
        self.crear_prestamo(usuario=self.usuario, libro=self.libro)
        self.crear_prestamo(usuario=self.usuario, libro=self.libro)

        response = self.client.get(reverse('prestamo-list'))

        self.assert_envelope_exitosa(response)
        self.assertEqual(len(response.data['datos']), 2)

    def test_crear_prestamo(self):
        hoy = date.today()
        response = self.client.post(
            reverse('prestamo-list'),
            {'id_usuario': self.usuario.id,
             'id_libro': self.libro.id_libro,
             'fecha_prestamo': hoy.isoformat(),
             'fecha_devolucion': (hoy + timedelta(days=7)).isoformat()},
            format='json',
        )

        self.assert_envelope_exitosa(response, HTTP_201_CREATED)
        self.assertEqual(Prestamo.objects.count(), 1)
        prestamo = Prestamo.objects.get()
        self.assertEqual(response.data['datos']['id_prestamo'], prestamo.id_prestamo)
        self.assertEqual(response.data['datos']['estado'], Prestamo.ESTADO_PRESTADO)

    def test_ver_prestamo_por_id(self):
        prestamo = self.crear_prestamo(usuario=self.usuario, libro=self.libro)

        response = self.client.get(
            reverse('prestamo-detail', args=[prestamo.id_prestamo]))

        self.assert_envelope_exitosa(response)
        self.assertEqual(response.data['datos']['id_prestamo'], prestamo.id_prestamo)
        self.assertEqual(response.data['datos']['estado'], Prestamo.ESTADO_PRESTADO)

    def test_actualizar_prestamo(self):
        prestamo = self.crear_prestamo(usuario=self.usuario, libro=self.libro)
        hoy = date.today()

        response = self.client.put(
            reverse('prestamo-detail', args=[prestamo.id_prestamo]),
            {'id_usuario': self.usuario.id,
             'id_libro': self.libro.id_libro,
             'fecha_prestamo': hoy.isoformat(),
             'fecha_devolucion': (hoy + timedelta(days=7)).isoformat()},
            format='json',
        )

        self.assert_envelope_exitosa(response)
        prestamo.refresh_from_db()
        self.assertEqual(prestamo.fecha_devolucion, hoy + timedelta(days=7))
        self.assertEqual(prestamo.estado, Prestamo.ESTADO_PRESTADO)

    def test_eliminar_prestamo(self):
        prestamo = self.crear_prestamo(usuario=self.usuario, libro=self.libro)

        response = self.client.delete(
            reverse('prestamo-detail', args=[prestamo.id_prestamo]))

        self.assert_envelope_exitosa(response)
        self.assertEqual(Prestamo.objects.count(), 0)

    def test_paginador_prestamos(self):
        for _ in range(12):
            self.crear_prestamo(usuario=self.usuario, libro=self.libro)

        pagina1 = self.client.get(f"{reverse('prestamo-paginar')}?page=1")
        self.assert_envelope_exitosa(pagina1)
        self.assertEqual(len(pagina1.data['datos']), PAGE_SIZE)
        self.assertFalse(pagina1.data['previous'])
        self.assertTrue(pagina1.data['next'])
        self.assertEqual(pagina1.data['maxPages'], 2)

        pagina2 = self.client.get(f"{reverse('prestamo-paginar')}?page=2")
        self.assert_envelope_exitosa(pagina2)
        self.assertEqual(len(pagina2.data['datos']), 2)
        self.assertTrue(pagina2.data['previous'])
        self.assertFalse(pagina2.data['next'])

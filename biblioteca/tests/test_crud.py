"""Cobertura CRUD básico de las cuatro entidades: Categorias, Libros,
Usuarios y Prestamos.

Verifica listar, crear, ver por id, actualizar, eliminar y paginación,
comprobando el envelope JSON y los status codes de cada endpoint.
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
        response = self.client.get(reverse('categorias_list'))

        self.assert_envelope_exitosa(response)
        self.assertEqual(response.data['datos'], [])

    def test_listar_categorias(self):
        self.crear_categoria(nombre='Ficción')
        self.crear_categoria(nombre='Terror')

        response = self.client.get(reverse('categorias_list'))

        self.assert_envelope_exitosa(response)
        self.assertEqual(len(response.data['datos']), 2)
        nombres = {item['nombre'] for item in response.data['datos']}
        self.assertEqual(nombres, {'Ficción', 'Terror'})

    def test_crear_categoria(self):
        response = self.client.post(
            reverse('Categoria_add'),
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

        url = f"{reverse('Categoria_view')}?id_categoria={categoria.id_categoria}"
        response = self.client.get(url)

        self.assert_envelope_exitosa(response)
        # La vista devuelve el objeto dentro de una lista.
        self.assertIsInstance(response.data['datos'], list)
        self.assertEqual(len(response.data['datos']), 1)
        self.assertEqual(response.data['datos'][0]['id_categoria'], categoria.id_categoria)
        self.assertEqual(response.data['datos'][0]['nombre'], 'Ficción')

    def test_actualizar_categoria(self):
        categoria = self.crear_categoria(nombre='Ficción', descripcion='Antes')

        response = self.client.put(
            reverse('Categoria_update'),
            {'id_categoria': categoria.id_categoria, 'nombre': 'Terror',
             'descripcion': 'Después'},
            format='json',
        )

        self.assert_envelope_exitosa(response)
        categoria.refresh_from_db()
        self.assertEqual(categoria.nombre, 'Terror')
        self.assertEqual(categoria.descripcion, 'Después')

    def test_eliminar_categoria(self):
        categoria = self.crear_categoria()

        url = f"{reverse('Categoria_delete')}?id_categoria={categoria.id_categoria}"
        response = self.client.delete(url)

        self.assert_envelope_exitosa(response)
        self.assertEqual(Categoria.objects.count(), 0)

    def test_paginador_categorias(self):
        for i in range(12):
            self.crear_categoria(nombre=f'Categoría {i}')

        pagina1 = self.client.get(f"{reverse('Categoria_paginator')}?page=1")
        self.assert_envelope_exitosa(pagina1)
        self.assertEqual(len(pagina1.data['datos']), PAGE_SIZE)
        self.assertFalse(pagina1.data['previous'])
        self.assertTrue(pagina1.data['next'])
        self.assertEqual(pagina1.data['maxPages'], 2)
        self.assertEqual(pagina1.data['currentpage'], 1)

        pagina2 = self.client.get(f"{reverse('Categoria_paginator')}?page=2")
        self.assert_envelope_exitosa(pagina2)
        self.assertEqual(len(pagina2.data['datos']), 2)
        self.assertTrue(pagina2.data['previous'])
        self.assertFalse(pagina2.data['next'])

    def test_paginador_categorias_con_filtro(self):
        self.crear_categoria(nombre='Ficción', descripcion='Ciencia')
        self.crear_categoria(nombre='Terror', descripcion='Suspenso')

        url = f"{reverse('Categoria_paginator')}?page=1&filter=fic"
        response = self.client.get(url)

        self.assert_envelope_exitosa(response)
        self.assertEqual(len(response.data['datos']), 1)
        self.assertEqual(response.data['datos'][0]['nombre'], 'Ficción')


class LibrosCRUDTests(BaseAPITest):
    """CRUD y paginación del recurso Libros."""

    def setUp(self):
        self.categoria = self.crear_categoria(nombre='Ficción')

    def test_listar_libros_vacia(self):
        response = self.client.get(reverse('libros_list'))

        self.assert_envelope_exitosa(response)
        self.assertEqual(response.data['datos'], [])

    def test_listar_libros(self):
        self.crear_libro(titulo='Dune', autor='Frank Herbert', isbn='978-1',
                         categoria=self.categoria)
        self.crear_libro(titulo='Neuromante', autor='William Gibson', isbn='978-2',
                         categoria=self.categoria)

        response = self.client.get(reverse('libros_list'))

        self.assert_envelope_exitosa(response)
        self.assertEqual(len(response.data['datos']), 2)
        titulos = {item['titulo'] for item in response.data['datos']}
        self.assertEqual(titulos, {'Dune', 'Neuromante'})

    def test_crear_libro(self):
        response = self.client.post(
            reverse('Libro_add'),
            {'titulo': 'Dune', 'autor': 'Frank Herbert', 'isbn': '978-3',
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
            reverse('Libro_add'),
            {'titulo': 'Dune', 'autor': 'Frank Herbert', 'isbn': '978-4',
             'id_categoria': self.categoria.id_categoria},
            format='json',
        )

        self.assert_envelope_exitosa(response, HTTP_201_CREATED)
        self.assertEqual(response.data['datos']['cantidad'], 1)

    def test_ver_libro_por_id(self):
        libro = self.crear_libro(titulo='Dune', isbn='978-5', categoria=self.categoria)

        url = f"{reverse('Libro_view')}?id_libro={libro.id_libro}"
        response = self.client.get(url)

        self.assert_envelope_exitosa(response)
        self.assertIsInstance(response.data['datos'], list)
        self.assertEqual(len(response.data['datos']), 1)
        self.assertEqual(response.data['datos'][0]['id_libro'], libro.id_libro)
        self.assertEqual(response.data['datos'][0]['titulo'], 'Dune')

    def test_actualizar_libro(self):
        libro = self.crear_libro(titulo='Dune', autor='Frank Herbert',
                                 isbn='978-6', cantidad=4, categoria=self.categoria)

        response = self.client.put(
            reverse('Libro_update'),
            {'id_libro': libro.id_libro, 'titulo': 'Dune 2', 'autor': 'Frank Herbert',
             'isbn': '978-6', 'cantidad': 7, 'id_categoria': self.categoria.id_categoria},
            format='json',
        )

        self.assert_envelope_exitosa(response)
        libro.refresh_from_db()
        self.assertEqual(libro.titulo, 'Dune 2')
        self.assertEqual(libro.cantidad, 7)

    def test_eliminar_libro(self):
        libro = self.crear_libro(isbn='978-7', categoria=self.categoria)

        url = f"{reverse('Libro_delete')}?id_libro={libro.id_libro}"
        response = self.client.delete(url)

        self.assert_envelope_exitosa(response)
        self.assertEqual(Libro.objects.count(), 0)

    def test_paginador_libros(self):
        for i in range(12):
            self.crear_libro(titulo=f'Libro {i}', isbn=f'978-{i:04d}',
                             categoria=self.categoria)

        pagina1 = self.client.get(f"{reverse('Libro_paginator')}?page=1")
        self.assert_envelope_exitosa(pagina1)
        self.assertEqual(len(pagina1.data['datos']), PAGE_SIZE)
        self.assertFalse(pagina1.data['previous'])
        self.assertTrue(pagina1.data['next'])
        self.assertEqual(pagina1.data['maxPages'], 2)

        pagina2 = self.client.get(f"{reverse('Libro_paginator')}?page=2")
        self.assert_envelope_exitosa(pagina2)
        self.assertEqual(len(pagina2.data['datos']), 2)
        self.assertTrue(pagina2.data['previous'])
        self.assertFalse(pagina2.data['next'])


class UsuariosCRUDTests(BaseAPITest):
    """CRUD y paginación del recurso Usuarios."""

    def test_listar_usuarios_vacia(self):
        response = self.client.get(reverse('usuarios_list'))

        self.assert_envelope_exitosa(response)
        self.assertEqual(response.data['datos'], [])

    def test_listar_usuarios(self):
        self.crear_usuario(nombre='Juan', apellido='Perez', correo='juan@test.com')
        self.crear_usuario(nombre='Ana', apellido='Lopez', correo='ana@test.com')

        response = self.client.get(reverse('usuarios_list'))

        self.assert_envelope_exitosa(response)
        self.assertEqual(len(response.data['datos']), 2)
        correos = {item['correo'] for item in response.data['datos']}
        self.assertEqual(correos, {'juan@test.com', 'ana@test.com'})

    def test_crear_usuario(self):
        response = self.client.post(
            reverse('Usuario_add'),
            {'nombre': 'Juan', 'apellido': 'Perez', 'correo': 'juan@test.com',
             'contrasena': 'clave-secreta-1', 'telefono': '555-1234'},
            format='json',
        )

        self.assert_envelope_exitosa(response, HTTP_201_CREATED)
        self.assertEqual(Usuario.objects.count(), 1)
        usuario = Usuario.objects.get()
        self.assertEqual(response.data['datos']['id_usuario'], usuario.id_usuario)
        self.assertEqual(response.data['datos']['correo'], 'juan@test.com')

    def test_ver_usuario_por_id(self):
        usuario = self.crear_usuario(correo='juan@test.com')

        url = f"{reverse('Usuario_view')}?id_usuario={usuario.id_usuario}"
        response = self.client.get(url)

        self.assert_envelope_exitosa(response)
        self.assertIsInstance(response.data['datos'], list)
        self.assertEqual(len(response.data['datos']), 1)
        self.assertEqual(response.data['datos'][0]['id_usuario'], usuario.id_usuario)
        self.assertEqual(response.data['datos'][0]['correo'], 'juan@test.com')

    def test_actualizar_usuario(self):
        usuario = self.crear_usuario(nombre='Juan', apellido='Perez',
                                     correo='juan@test.com')

        response = self.client.put(
            reverse('Usuario_update'),
            {'id_usuario': usuario.id_usuario, 'nombre': 'Juan Carlos',
             'apellido': 'Perez', 'correo': 'juan@test.com',
             'contrasena': 'nueva-clave-1', 'telefono': '555-9999'},
            format='json',
        )

        self.assert_envelope_exitosa(response)
        usuario.refresh_from_db()
        self.assertEqual(usuario.nombre, 'Juan Carlos')
        self.assertEqual(usuario.telefono, '555-9999')
        self.assertTrue(usuario.check_contrasena('nueva-clave-1'))

    def test_actualizar_usuario_sin_contrasena_conserva_clave(self):
        usuario = self.crear_usuario(nombre='Juan', apellido='Perez',
                                     correo='juan@test.com',
                                     contrasena='clave-original')

        response = self.client.put(
            reverse('Usuario_update'),
            {'id_usuario': usuario.id_usuario, 'nombre': 'Juan Carlos',
             'apellido': 'Perez', 'correo': 'juan@test.com',
             'telefono': '555-0000'},  # sin contrasena
            format='json',
        )

        self.assert_envelope_exitosa(response)
        usuario.refresh_from_db()
        self.assertEqual(usuario.nombre, 'Juan Carlos')
        self.assertEqual(usuario.telefono, '555-0000')
        # La contraseña antigua sigue siendo válida: no se pisó el hash.
        self.assertTrue(usuario.check_contrasena('clave-original'))

    def test_eliminar_usuario(self):
        usuario = self.crear_usuario(correo='juan@test.com')

        url = f"{reverse('Usuario_delete')}?id_usuario={usuario.id_usuario}"
        response = self.client.delete(url)

        self.assert_envelope_exitosa(response)
        self.assertEqual(Usuario.objects.count(), 0)

    def test_paginador_usuarios(self):
        for i in range(12):
            self.crear_usuario(nombre=f'Usuario {i}', apellido='Test',
                               correo=f'usuario{i}@test.com')

        pagina1 = self.client.get(f"{reverse('Usuario_paginator')}?page=1")
        self.assert_envelope_exitosa(pagina1)
        self.assertEqual(len(pagina1.data['datos']), PAGE_SIZE)
        self.assertFalse(pagina1.data['previous'])
        self.assertTrue(pagina1.data['next'])
        self.assertEqual(pagina1.data['maxPages'], 2)

        pagina2 = self.client.get(f"{reverse('Usuario_paginator')}?page=2")
        self.assert_envelope_exitosa(pagina2)
        self.assertEqual(len(pagina2.data['datos']), 2)
        self.assertTrue(pagina2.data['previous'])
        self.assertFalse(pagina2.data['next'])


class PrestamosCRUDTests(BaseAPITest):
    """CRUD y paginación del recurso Prestamos."""

    def setUp(self):
        self.usuario = self.crear_usuario(correo='juan@test.com')
        self.libro = self.crear_libro(titulo='Dune', isbn='978-11', cantidad=5)

    def test_listar_prestamos_vacia(self):
        response = self.client.get(reverse('prestamos_list'))

        self.assert_envelope_exitosa(response)
        self.assertEqual(response.data['datos'], [])

    def test_listar_prestamos(self):
        self.crear_prestamo(usuario=self.usuario, libro=self.libro)
        self.crear_prestamo(usuario=self.usuario, libro=self.libro)

        response = self.client.get(reverse('prestamos_list'))

        self.assert_envelope_exitosa(response)
        self.assertEqual(len(response.data['datos']), 2)

    def test_crear_prestamo(self):
        hoy = date.today()
        response = self.client.post(
            reverse('Prestamo_add'),
            {'id_usuario': self.usuario.id_usuario,
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

        url = f"{reverse('Prestamo_view')}?id_prestamo={prestamo.id_prestamo}"
        response = self.client.get(url)

        self.assert_envelope_exitosa(response)
        self.assertIsInstance(response.data['datos'], list)
        self.assertEqual(len(response.data['datos']), 1)
        self.assertEqual(response.data['datos'][0]['id_prestamo'], prestamo.id_prestamo)
        self.assertEqual(response.data['datos'][0]['estado'], Prestamo.ESTADO_PRESTADO)

    def test_actualizar_prestamo(self):
        prestamo = self.crear_prestamo(usuario=self.usuario, libro=self.libro)
        hoy = date.today()

        response = self.client.put(
            reverse('Prestamo_update'),
            {'id_prestamo': prestamo.id_prestamo,
             'id_usuario': self.usuario.id_usuario,
             'id_libro': self.libro.id_libro,
             'fecha_prestamo': hoy.isoformat(),
             'fecha_devolucion': (hoy + timedelta(days=14)).isoformat()},
            format='json',
        )

        self.assert_envelope_exitosa(response)
        prestamo.refresh_from_db()
        self.assertEqual(prestamo.fecha_devolucion, hoy + timedelta(days=14))
        self.assertEqual(prestamo.estado, Prestamo.ESTADO_PRESTADO)

    def test_eliminar_prestamo(self):
        prestamo = self.crear_prestamo(usuario=self.usuario, libro=self.libro)

        url = f"{reverse('Prestamo_delete')}?id_prestamo={prestamo.id_prestamo}"
        response = self.client.delete(url)

        self.assert_envelope_exitosa(response)
        self.assertEqual(Prestamo.objects.count(), 0)

    def test_paginador_prestamos(self):
        for _ in range(12):
            self.crear_prestamo(usuario=self.usuario, libro=self.libro)

        pagina1 = self.client.get(f"{reverse('Prestamo_paginator')}?page=1")
        self.assert_envelope_exitosa(pagina1)
        self.assertEqual(len(pagina1.data['datos']), PAGE_SIZE)
        self.assertFalse(pagina1.data['previous'])
        self.assertTrue(pagina1.data['next'])
        self.assertEqual(pagina1.data['maxPages'], 2)

        pagina2 = self.client.get(f"{reverse('Prestamo_paginator')}?page=2")
        self.assert_envelope_exitosa(pagina2)
        self.assertEqual(len(pagina2.data['datos']), 2)
        self.assertTrue(pagina2.data['previous'])
        self.assertFalse(pagina2.data['next'])
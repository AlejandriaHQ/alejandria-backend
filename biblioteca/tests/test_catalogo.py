"""Cobertura del Catálogo (RF-05 a RF-10, RN-06/07/09).

Verifica la ficha bibliográfica ampliada del Libro (anio, editorial,
descripcion, portada), la disponibilidad calculada (total/prestados/
disponibles), la búsqueda combinable (isbn, categoria, filtros combinados),
la eliminación lógica de libros y categorías (libro con préstamos se
desactiva, inactivo no aparece en listado) y la validación del formato ISBN.
"""
from django.urls import reverse
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST

from biblioteca.models import Categoria, Libro, Prestamo
from biblioteca.tests.helpers import BaseAPITest

# ISBN-13 válidos (formato, no checksum). Únicos dentro de cada test.
ISBN_DUNE = '9780306406157'
ISBN_NEUROMANTE = '9780451524935'
ISBN_1984 = '9780451524936'
ISBN_OTRO = '9780743273565'


class LibroFichaBibliograficaTests(BaseAPITest):
    """RF-05: creación/persistencia de la ficha bibliográfica ampliada."""

    def setUp(self):
        super().setUp()
        self.categoria = self.crear_categoria(nombre='Ficción')

    def test_crear_libro_con_anio_editorial_descripcion_portada(self):
        response = self.client.post(
            reverse('libro-list'),
            {
                'titulo': 'Dune',
                'autor': 'Frank Herbert',
                'isbn': ISBN_DUNE,
                'cantidad': 4,
                'id_categoria': self.categoria.id_categoria,
                'anio': 1965,
                'editorial': 'Chilton Books',
                'descripcion': 'Primera novela de la saga Dune.',
                'portada': 'https://ejemplo.com/portadas/dune.jpg',
            },
            format='json',
        )

        self.assert_envelope_exitosa(response, HTTP_201_CREATED)
        libro = Libro.objects.get()
        self.assertEqual(libro.anio, 1965)
        self.assertEqual(libro.editorial, 'Chilton Books')
        self.assertEqual(libro.descripcion, 'Primera novela de la saga Dune.')
        self.assertEqual(libro.portada, 'https://ejemplo.com/portadas/dune.jpg')
        self.assertTrue(libro.activo)

    def test_libro_sin_datos_opcionales_usa_opcionales_vacios(self):
        response = self.client.post(
            reverse('libro-list'),
            {'titulo': 'Solo', 'autor': 'Autor',
             'isbn': ISBN_OTRO, 'id_categoria': self.categoria.id_categoria},
            format='json',
        )

        self.assert_envelope_exitosa(response, HTTP_201_CREATED)
        libro = Libro.objects.get()
        self.assertIsNone(libro.anio)
        self.assertIsNone(libro.editorial)
        self.assertIsNone(libro.portada)


class LibroDisponibilidadTests(BaseAPITest):
    """RF-09: total / prestados / disponibles del Libro."""

    def setUp(self):
        super().setUp()
        self.categoria = self.crear_categoria(nombre='Ficción')

    def test_sin_prestamos_todo_disponible(self):
        libro = self.crear_libro(titulo='Dune', isbn=ISBN_DUNE,
                                 cantidad=5, categoria=self.categoria)

        self.assertEqual(libro.prestados(), 0)
        self.assertEqual(libro.disponibles(), 5)

    def test_prestados_y_disponibles(self):
        libro = self.crear_libro(titulo='Dune', isbn=ISBN_DUNE,
                                 cantidad=5, categoria=self.categoria)
        self.crear_prestamo(libro=libro, estado=Prestamo.ESTADO_PRESTADO)
        # Un préstamo devuelto no cuenta como activo ni resta disponibilidad.
        self.crear_prestamo(libro=libro, estado=Prestamo.ESTADO_DEVUELTO)

        self.assertEqual(libro.prestados(), 1)
        self.assertEqual(libro.disponibles(), 4)

    def test_prestados_incluye_atrasado(self):
        libro = self.crear_libro(titulo='Dune', isbn=ISBN_DUNE,
                                 cantidad=3, categoria=self.categoria)
        self.crear_prestamo(libro=libro, estado=Prestamo.ESTADO_PRESTADO)
        self.crear_prestamo(libro=libro, estado=Prestamo.ESTADO_ATRASADO)

        self.assertEqual(libro.prestados(), 2)
        self.assertEqual(libro.disponibles(), 1)

    def test_detalle_expone_prestados_y_disponibles(self):
        libro = self.crear_libro(titulo='Dune', isbn=ISBN_DUNE,
                                 cantidad=5, categoria=self.categoria)
        self.crear_prestamo(libro=libro, estado=Prestamo.ESTADO_PRESTADO)

        response = self.client.get(reverse('libro-detail', args=[libro.id_libro]))

        self.assert_envelope_exitosa(response)
        self.assertEqual(response.data['datos']['prestados'], 1)
        self.assertEqual(response.data['datos']['disponibles'], 4)


class LibroBusquedaCombinableTests(BaseAPITest):
    """RF-08: búsqueda por isbn, por categoria y combinada."""

    def setUp(self):
        super().setUp()
        self.cat_ficcion = self.crear_categoria(nombre='Ficción')
        self.cat_ciencia = self.crear_categoria(nombre='Ciencia')
        self.libro_dune = self.crear_libro(titulo='Dune', autor='Frank Herbert',
                                           isbn=ISBN_DUNE, categoria=self.cat_ficcion)
        self.libro_neuromante = self.crear_libro(titulo='Neuromante',
                                                 autor='William Gibson',
                                                 isbn=ISBN_NEUROMANTE,
                                                 categoria=self.cat_ciencia)

    def test_buscar_por_isbn(self):
        url = f"{reverse('libro-paginar')}?page=1&filter={ISBN_DUNE}"
        response = self.client.get(url)

        self.assert_envelope_exitosa(response)
        self.assertEqual(len(response.data['datos']), 1)
        self.assertEqual(response.data['datos'][0]['isbn'], ISBN_DUNE)

    def test_buscar_por_categoria(self):
        url = f"{reverse('libro-paginar')}?page=1&categoria={self.cat_ficcion.id_categoria}"
        response = self.client.get(url)

        self.assert_envelope_exitosa(response)
        self.assertEqual(len(response.data['datos']), 1)
        self.assertEqual(response.data['datos'][0]['titulo'], 'Dune')

    def test_buscar_combinada_filter_y_categoria(self):
        # Combina filtro por texto (OR titulo/autor/isbn) y categoria (AND).
        url = (f"{reverse('libro-paginar')}?page=1&filter=Dune"
               f"&categoria={self.cat_ficcion.id_categoria}")
        response = self.client.get(url)

        self.assert_envelope_exitosa(response)
        self.assertEqual(len(response.data['datos']), 1)
        self.assertEqual(response.data['datos'][0]['titulo'], 'Dune')

    def test_categoria_no_numerica_rechazada(self):
        url = f"{reverse('libro-paginar')}?page=1&categoria=abc"
        response = self.client.get(url)

        self.assert_envelope_error(response)
        self.assertEqual(response.data['Mensaje'],
                         'El parámetro categoria debe ser un número entero')


class LibroEliminacionLogicaTests(BaseAPITest):
    """RN-06 / RF-07: libros con préstamos se desactivan, no se borran."""

    def setUp(self):
        super().setUp()
        self.categoria = self.crear_categoria(nombre='Ficción')

    def test_eliminar_libro_con_prestamos_desactiva(self):
        libro = self.crear_libro(titulo='Dune', isbn=ISBN_DUNE,
                                 cantidad=5, categoria=self.categoria)
        self.crear_prestamo(libro=libro, estado=Prestamo.ESTADO_PRESTADO)

        response = self.client.delete(reverse('libro-detail', args=[libro.id_libro]))

        self.assert_envelope_exitosa(response)
        self.assertIn('desactivó', response.data['Mensaje'])
        libro.refresh_from_db()
        self.assertFalse(libro.activo)
        # El libro no se borró físicamente (conserva el historial de préstamos).
        self.assertTrue(Libro.objects.filter(pk=libro.pk).exists())

    def test_eliminar_libro_con_historial_devuelto_desactiva(self):
        # Un préstamo DEVUELTO es historial: el libro tampoco se borra.
        libro = self.crear_libro(titulo='Dune', isbn=ISBN_DUNE,
                                 cantidad=5, categoria=self.categoria)
        self.crear_prestamo(libro=libro, estado=Prestamo.ESTADO_DEVUELTO)

        response = self.client.delete(reverse('libro-detail', args=[libro.id_libro]))

        self.assert_envelope_exitosa(response)
        libro.refresh_from_db()
        self.assertFalse(libro.activo)
        self.assertTrue(Libro.objects.filter(pk=libro.pk).exists())

    def test_eliminar_libro_sin_prestamos_borra_fisicamente(self):
        libro = self.crear_libro(titulo='Dune', isbn=ISBN_DUNE,
                                 cantidad=5, categoria=self.categoria)

        response = self.client.delete(reverse('libro-detail', args=[libro.id_libro]))

        self.assert_envelope_exitosa(response)
        self.assertEqual(Libro.objects.filter(pk=libro.pk).count(), 0)

    def test_libro_inactivo_no_aparece_en_listado_ni_paginador(self):
        libro_con_prestamos = self.crear_libro(titulo='Dune', isbn=ISBN_DUNE,
                                               cantidad=5, categoria=self.categoria)
        self.crear_prestamo(libro=libro_con_prestamos, estado=Prestamo.ESTADO_PRESTADO)
        self.client.delete(
            reverse('libro-detail', args=[libro_con_prestamos.id_libro]))

        libro_activo = self.crear_libro(titulo='Neuromante', isbn=ISBN_NEUROMANTE,
                                        cantidad=3, categoria=self.categoria)

        lista = self.client.get(reverse('libro-list'))
        self.assert_envelope_exitosa(lista)
        self.assertEqual(len(lista.data['datos']), 1)
        self.assertEqual(lista.data['datos'][0]['titulo'], 'Neuromante')

        paginador = self.client.get(f"{reverse('libro-paginar')}?page=1")
        self.assert_envelope_exitosa(paginador)
        self.assertEqual(len(paginador.data['datos']), 1)
        self.assertEqual(paginador.data['datos'][0]['titulo'], 'Neuromante')


class CategoriaEliminacionLogicaTests(BaseAPITest):
    """RN-07 / RF-10: categorías con libros se desactivan, no se borran."""

    def test_eliminar_categoria_con_libros_desactiva(self):
        categoria = self.crear_categoria(nombre='Ficción')
        self.crear_libro(titulo='Dune', isbn=ISBN_DUNE, categoria=categoria)

        response = self.client.delete(
            reverse('categoria-detail', args=[categoria.id_categoria]))

        self.assert_envelope_exitosa(response)
        self.assertIn('desactivó', response.data['Mensaje'])
        categoria.refresh_from_db()
        self.assertFalse(categoria.activo)
        self.assertTrue(Categoria.objects.filter(pk=categoria.pk).exists())

    def test_categoria_sin_libros_se_borra_fisicamente(self):
        categoria = self.crear_categoria(nombre='Vacía')

        response = self.client.delete(
            reverse('categoria-detail', args=[categoria.id_categoria]))

        self.assert_envelope_exitosa(response)
        self.assertEqual(Categoria.objects.filter(pk=categoria.pk).count(), 0)

    def test_categoria_inactiva_no_aparece_en_listado(self):
        categoria_inactiva = self.crear_categoria(nombre='Ficción')
        self.crear_libro(titulo='Dune', isbn=ISBN_DUNE, categoria=categoria_inactiva)
        self.client.delete(
            reverse('categoria-detail', args=[categoria_inactiva.id_categoria]))

        self.crear_categoria(nombre='Ciencia')
        self.crear_categoria(nombre='Terror')

        response = self.client.get(reverse('categoria-list'))

        self.assert_envelope_exitosa(response)
        nombres = {item['nombre'] for item in response.data['datos']}
        self.assertEqual(nombres, {'Ciencia', 'Terror'})


class LibroISBNTests(BaseAPITest):
    """RN-09: validación de formato del ISBN."""

    def setUp(self):
        super().setUp()
        self.categoria = self.crear_categoria(nombre='Ficción')

    def test_isbn_invalido_rechazado(self):
        response = self.client.post(
            reverse('libro-list'),
            {'titulo': 'Dune', 'autor': 'Frank Herbert', 'isbn': '123',
             'id_categoria': self.categoria.id_categoria},
            format='json',
        )

        self.assert_envelope_error(response, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['Mensaje']['isbn'][0],
                         'El ISBN no tiene un formato válido')

    def test_isbn_se_aceptan_guiones_y_espacios(self):
        # '978-0-306-40615-7' (con guiones) es el mismo ISBN-13 válido.
        response = self.client.post(
            reverse('libro-list'),
            {'titulo': 'Dune', 'autor': 'Frank Herbert',
             'isbn': '978-0-306-40615-7',
             'id_categoria': self.categoria.id_categoria},
            format='json',
        )

        self.assert_envelope_exitosa(response, HTTP_201_CREATED)

    def test_isbn_10_con_x_aceptado(self):
        response = self.client.post(
            reverse('libro-list'),
            {'titulo': 'Obra', 'autor': 'Autor', 'isbn': '030640615X',
             'id_categoria': self.categoria.id_categoria},
            format='json',
        )

        self.assert_envelope_exitosa(response, HTTP_201_CREATED)

    def test_isbn_invalido_rechazado_en_update(self):
        libro = self.crear_libro(titulo='Dune', isbn=ISBN_DUNE,
                                 categoria=self.categoria)

        response = self.client.put(
            reverse('libro-detail', args=[libro.id_libro]),
            {'titulo': 'Dune', 'autor': 'Frank Herbert', 'isbn': '1234',
             'id_categoria': self.categoria.id_categoria},
            format='json',
        )

        self.assert_envelope_error(response, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['Mensaje']['isbn'][0],
                         'El ISBN no tiene un formato válido')

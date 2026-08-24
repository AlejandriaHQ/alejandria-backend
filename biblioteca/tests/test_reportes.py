from datetime import date

from rest_framework.status import HTTP_403_FORBIDDEN

from biblioteca.tests.helpers import BaseAPITest
from biblioteca.models import Prestamo


class ReportesTests(BaseAPITest):
    # ------------------------------------------------------------------ #
    # RF-26 / CU-15 — Dashboard
    # ------------------------------------------------------------------ #
    def test_dashboard_devuelve_totales(self):
        libro = self.crear_libro()
        usuario = self.crear_usuario()
        self.crear_prestamo(usuario=usuario, libro=libro)

        response = self.client.get('/biblioteca/reportes/dashboard/')
        self.assert_envelope_exitosa(response)

        datos = response.data['datos']
        for clave in ('total_libros', 'total_usuarios',
                      'prestamos_activos', 'vencidos', 'prestamos_del_mes'):
            self.assertIn(clave, datos)

        # El préstamo creado está activo (Prestado), por lo que debe contar.
        self.assertGreaterEqual(datos['prestamos_activos'], 1)

    # ------------------------------------------------------------------ #
    # RF-27 — Préstamos por rango de fechas
    # ------------------------------------------------------------------ #
    def test_prestamos_por_rango(self):
        usuario = self.crear_usuario()
        libro = self.crear_libro()
        # Dos préstamos DENTRO del rango.
        self.crear_prestamo(usuario=usuario, libro=libro, fecha_prestamo=date(2025, 1, 10))
        self.crear_prestamo(usuario=usuario, libro=libro, fecha_prestamo=date(2025, 1, 20))
        # Un préstamo FUERA del rango.
        self.crear_prestamo(usuario=usuario, libro=libro, fecha_prestamo=date(2024, 6, 1))

        response = self.client.get(
            '/biblioteca/reportes/prestamos/?desde=2025-01-01&hasta=2025-01-31'
        )
        self.assert_envelope_exitosa(response)

        datos = response.data['datos']
        self.assertEqual(datos['total'], 2)
        self.assertEqual(len(datos['prestamos']), 2)
        self.assertEqual(datos['rango']['desde'], '2025-01-01')
        self.assertEqual(datos['rango']['hasta'], '2025-01-31')

    # ------------------------------------------------------------------ #
    # RF-28 — Devoluciones por rango de fechas
    # ------------------------------------------------------------------ #
    def test_devoluciones_por_rango(self):
        usuario = self.crear_usuario()
        libro = self.crear_libro()
        # Devolución DENTRO del rango.
        p_dentro = self.crear_prestamo(
            usuario=usuario, libro=libro,
            fecha_prestamo=date(2025, 3, 10), estado=Prestamo.ESTADO_DEVUELTO,
        )
        p_dentro.fecha_devolucion_real = date(2025, 3, 15)
        p_dentro.save()
        # Devolución FUERA del rango.
        p_fuera = self.crear_prestamo(
            usuario=usuario, libro=libro,
            fecha_prestamo=date(2024, 1, 1), estado=Prestamo.ESTADO_DEVUELTO,
        )
        p_fuera.fecha_devolucion_real = date(2024, 1, 10)
        p_fuera.save()

        response = self.client.get(
            '/biblioteca/reportes/devoluciones/?desde=2025-03-01&hasta=2025-03-31'
        )
        self.assert_envelope_exitosa(response)

        datos = response.data['datos']
        self.assertEqual(datos['total'], 1)
        self.assertEqual(len(datos['devoluciones']), 1)

    # ------------------------------------------------------------------ #
    # RF-29 — Inventario
    # ------------------------------------------------------------------ #
    def test_inventario(self):
        libro = self.crear_libro(cantidad=5)
        usuario = self.crear_usuario()
        # Dos préstamos activos del mismo libro.
        self.crear_prestamo(usuario=usuario, libro=libro)
        self.crear_prestamo(usuario=usuario, libro=libro)

        response = self.client.get('/biblioteca/reportes/inventario/')
        self.assert_envelope_exitosa(response)

        datos = response.data['datos']
        item = next(d for d in datos if d['libro'] == libro.titulo)
        self.assertEqual(item['cantidad'], 5)
        self.assertEqual(item['prestados'], 2)
        self.assertEqual(item['disponibles'], 3)
        self.assertEqual(item['disponibles'], item['cantidad'] - item['prestados'])

    # ------------------------------------------------------------------ #
    # RF-30 — Top libros más prestados
    # ------------------------------------------------------------------ #
    def test_top_libros(self):
        libro_top = self.crear_libro(titulo='Libro Top')
        usuario = self.crear_usuario()
        for _ in range(5):
            self.crear_prestamo(usuario=usuario, libro=libro_top)
        libro_otro = self.crear_libro(titulo='Libro Otro')
        self.crear_prestamo(usuario=usuario, libro=libro_otro)

        response = self.client.get('/biblioteca/reportes/top-libros/')
        self.assert_envelope_exitosa(response)

        datos = response.data['datos']
        self.assertEqual(datos[0]['id_libro'], libro_top.id_libro)
        self.assertEqual(datos[0]['titulo'], 'Libro Top')
        self.assertEqual(datos[0]['total_prestamos'], 5)

    # ------------------------------------------------------------------ #
    # RF-31 — Top usuarios con más préstamos
    # ------------------------------------------------------------------ #
    def test_top_usuarios(self):
        usuario_top = self.crear_usuario(first_name='Top', last_name='User')
        libro = self.crear_libro()
        for _ in range(4):
            self.crear_prestamo(usuario=usuario_top, libro=libro)
        usuario_otro = self.crear_usuario()
        self.crear_prestamo(usuario=usuario_otro, libro=libro)

        response = self.client.get('/biblioteca/reportes/top-usuarios/')
        self.assert_envelope_exitosa(response)

        datos = response.data['datos']
        self.assertEqual(datos[0]['id_usuario'], usuario_top.id)
        self.assertEqual(datos[0]['nombre'], 'Top User')
        self.assertEqual(datos[0]['total_prestamos'], 4)

    # ------------------------------------------------------------------ #
    # Protección por rol — un usuario normal no ve reportes
    # ------------------------------------------------------------------ #
    def test_proteccion_rol(self):
        usuario_normal = self.crear_usuario(role='user')
        self.autenticar_como(usuario_normal)

        response = self.client.get('/biblioteca/reportes/dashboard/')
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.assertFalse(response.data['success'])

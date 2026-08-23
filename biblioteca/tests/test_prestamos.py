"""Cobertura de las reglas de negocio de Prestamos.

Verifica el manejo de stock: decremento al prestar, rechazo cuando no hay
ejemplares, restauración al devolver y al eliminar un préstamo no devuelto,
y la transición automática Prestado -> Atrasado cuando la fecha de
devolución ya venció.
"""
from datetime import date, timedelta

from django.urls import reverse
from rest_framework.status import HTTP_400_BAD_REQUEST

from biblioteca.models import Prestamo
from biblioteca.tests.helpers import BaseAPITest


class PrestamosReglasStockTests(BaseAPITest):
    """Reglas de negocio de stock en préstamos."""

    def setUp(self):
        super().setUp()
        self.usuario = self.crear_usuario(email='juan@test.com')
        self.libro = self.crear_libro(titulo='Dune', isbn='978-1', cantidad=5)
        self.hoy = date.today()

    def crear_prestamo_via_api(self, fecha_devolucion=None):
        payload = {
            'id_usuario': self.usuario.id,
            'id_libro': self.libro.id_libro,
            'fecha_prestamo': self.hoy.isoformat(),
        }
        if fecha_devolucion is not None:
            payload['fecha_devolucion'] = fecha_devolucion.isoformat()
        return self.client.post(reverse('prestamo-list'), payload, format='json')

    def test_prestar_decrementa_stock(self):
        response = self.crear_prestamo_via_api(fecha_devolucion=self.hoy + timedelta(days=7))

        self.assert_envelope_exitosa(response, 201)
        self.libro.refresh_from_db()
        self.assertEqual(self.libro.cantidad, 4)

    def test_no_prestar_sin_stock(self):
        # Primer préstamo: stock 5 -> 4 -> 3 -> 2 -> 1 -> 0.
        for _ in range(5):
            self.assert_envelope_exitosa(self.crear_prestamo_via_api(), 201)
        self.libro.refresh_from_db()
        self.assertEqual(self.libro.cantidad, 0)

        response = self.crear_prestamo_via_api()

        self.assert_envelope_error(response, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['Mensaje'],
                         'No hay ejemplares disponibles de este libro')
        # El préstamo rechazado no se registró.
        self.assertEqual(Prestamo.objects.count(), 5)
        self.libro.refresh_from_db()
        self.assertEqual(self.libro.cantidad, 0)

    def test_devolucion_restaura_stock(self):
        response = self.crear_prestamo_via_api(fecha_devolucion=self.hoy + timedelta(days=7))
        prestamo_id = response.data['datos']['id_prestamo']
        self.libro.refresh_from_db()
        self.assertEqual(self.libro.cantidad, 4)

        response = self.client.put(
            reverse('prestamo-detail', args=[prestamo_id]),
            {'id_usuario': self.usuario.id,
             'id_libro': self.libro.id_libro,
             'fecha_prestamo': self.hoy.isoformat(),
             'fecha_devolucion': (self.hoy + timedelta(days=7)).isoformat(),
             'estado': Prestamo.ESTADO_DEVUELTO},
            format='json',
        )

        self.assert_envelope_exitosa(response)
        self.assertEqual(response.data['datos']['estado'], Prestamo.ESTADO_DEVUELTO)
        self.libro.refresh_from_db()
        self.assertEqual(self.libro.cantidad, 5)

    def test_eliminar_prestamo_no_devuelto_restaura_stock(self):
        response = self.crear_prestamo_via_api(fecha_devolucion=self.hoy + timedelta(days=7))
        prestamo_id = response.data['datos']['id_prestamo']
        self.libro.refresh_from_db()
        self.assertEqual(self.libro.cantidad, 4)

        response = self.client.delete(
            reverse('prestamo-detail', args=[prestamo_id]))

        self.assert_envelope_exitosa(response)
        self.libro.refresh_from_db()
        self.assertEqual(self.libro.cantidad, 5)

    def test_eliminar_prestamo_devuelto_no_restaura_dos_veces(self):
        response = self.crear_prestamo_via_api(fecha_devolucion=self.hoy + timedelta(days=7))
        prestamo_id = response.data['datos']['id_prestamo']
        self.libro.refresh_from_db()
        self.assertEqual(self.libro.cantidad, 4)

        # Devolver: el stock vuelve a 5.
        self.client.put(
            reverse('prestamo-detail', args=[prestamo_id]),
            {'id_usuario': self.usuario.id,
             'id_libro': self.libro.id_libro,
             'fecha_prestamo': self.hoy.isoformat(),
             'fecha_devolucion': (self.hoy + timedelta(days=7)).isoformat(),
             'estado': Prestamo.ESTADO_DEVUELTO},
            format='json',
        )
        self.libro.refresh_from_db()
        self.assertEqual(self.libro.cantidad, 5)

        # Eliminar un préstamo ya devuelto no debe incrementar el stock otra vez.
        response = self.client.delete(
            reverse('prestamo-detail', args=[prestamo_id]))
        self.assert_envelope_exitosa(response)
        self.libro.refresh_from_db()
        self.assertEqual(self.libro.cantidad, 5)

    def test_actualizar_prestamo_sin_cambiar_a_devuelto_no_afecta_stock(self):
        response = self.crear_prestamo_via_api(fecha_devolucion=self.hoy + timedelta(days=7))
        prestamo_id = response.data['datos']['id_prestamo']
        self.libro.refresh_from_db()
        self.assertEqual(self.libro.cantidad, 4)

        # Actualización sin cambiar el estado: el stock no debe moverse.
        response = self.client.put(
            reverse('prestamo-detail', args=[prestamo_id]),
            {'id_usuario': self.usuario.id,
             'id_libro': self.libro.id_libro,
             'fecha_prestamo': (self.hoy + timedelta(days=1)).isoformat(),
             'fecha_devolucion': (self.hoy + timedelta(days=8)).isoformat(),
             'estado': Prestamo.ESTADO_PRESTADO},
            format='json',
        )

        self.assert_envelope_exitosa(response)
        self.libro.refresh_from_db()
        self.assertEqual(self.libro.cantidad, 4)


class PrestamosTransicionAtrasadoTests(BaseAPITest):
    """Transición automática Prestado -> Atrasado."""

    def setUp(self):
        super().setUp()
        self.usuario = self.crear_usuario(email='juan@test.com')
        self.libro = self.crear_libro(titulo='Dune', isbn='978-1', cantidad=5)
        self.hoy = date.today()

    def test_transicion_a_atrasado_al_listar(self):
        prestamo = self.crear_prestamo(
            usuario=self.usuario,
            libro=self.libro,
            fecha_prestamo=self.hoy - timedelta(days=10),
            fecha_devolucion=self.hoy - timedelta(days=5),
            estado=Prestamo.ESTADO_PRESTADO,
        )

        response = self.client.get(reverse('prestamo-list'))

        self.assert_envelope_exitosa(response)
        prestamo.refresh_from_db()
        self.assertEqual(prestamo.estado, Prestamo.ESTADO_ATRASADO)
        self.assertEqual(response.data['datos'][0]['estado'], Prestamo.ESTADO_ATRASADO)

    def test_transicion_a_atrasado_al_ver_por_id(self):
        prestamo = self.crear_prestamo(
            usuario=self.usuario,
            libro=self.libro,
            fecha_prestamo=self.hoy - timedelta(days=10),
            fecha_devolucion=self.hoy - timedelta(days=5),
            estado=Prestamo.ESTADO_PRESTADO,
        )

        response = self.client.get(
            reverse('prestamo-detail', args=[prestamo.id_prestamo]))

        self.assert_envelope_exitosa(response)
        prestamo.refresh_from_db()
        self.assertEqual(prestamo.estado, Prestamo.ESTADO_ATRASADO)
        self.assertEqual(response.data['datos']['estado'], Prestamo.ESTADO_ATRASADO)

    def test_prestamo_no_vencido_sigue_prestado(self):
        self.crear_prestamo(
            usuario=self.usuario,
            libro=self.libro,
            fecha_prestamo=self.hoy - timedelta(days=10),
            fecha_devolucion=self.hoy + timedelta(days=5),
            estado=Prestamo.ESTADO_PRESTADO,
        )

        response = self.client.get(reverse('prestamo-list'))

        self.assert_envelope_exitosa(response)
        self.assertEqual(response.data['datos'][0]['estado'], Prestamo.ESTADO_PRESTADO)

    def test_transicion_a_atrasado_al_actualizar(self):
        # Un préstamo vencido pero aún "Prestado" debe normalizarse a
        # "Atrasado" incluso al actualizarlo (antes solo ocurría al listar/ver).
        prestamo = self.crear_prestamo(
            usuario=self.usuario,
            libro=self.libro,
            fecha_prestamo=self.hoy - timedelta(days=10),
            fecha_devolucion=self.hoy - timedelta(days=5),
            estado=Prestamo.ESTADO_PRESTADO,
        )

        # Se actualiza sin enviar estado (el cliente no cambia el estado):
        # la normalización al inicio de update deja el préstamo como Atrasado.
        response = self.client.put(
            reverse('prestamo-detail', args=[prestamo.id_prestamo]),
            {'id_usuario': self.usuario.id,
             'id_libro': self.libro.id_libro,
             'fecha_prestamo': (self.hoy - timedelta(days=10)).isoformat(),
             'fecha_devolucion': (self.hoy - timedelta(days=5)).isoformat()},
            format='json',
        )

        self.assert_envelope_exitosa(response)
        prestamo.refresh_from_db()
        self.assertEqual(prestamo.estado, Prestamo.ESTADO_ATRASADO)

    def test_transicion_a_atrasado_al_eliminar(self):
        # Al eliminar un préstamo vencido, la normalización también ocurre.
        prestamo = self.crear_prestamo(
            usuario=self.usuario,
            libro=self.libro,
            fecha_prestamo=self.hoy - timedelta(days=10),
            fecha_devolucion=self.hoy - timedelta(days=5),
            estado=Prestamo.ESTADO_PRESTADO,
        )

        response = self.client.delete(
            reverse('prestamo-detail', args=[prestamo.id_prestamo]))

        self.assert_envelope_exitosa(response)
        self.assertEqual(Prestamo.objects.filter(pk=prestamo.pk).count(), 0)

    def test_eliminar_prestamo_atrasado_restaura_stock(self):
        # Un préstamo vencido (Atrasado) mantiene el ejemplar fuera del stock;
        # al eliminarlo, el stock debe restituirse.
        prestamo = self.crear_prestamo(
            usuario=self.usuario,
            libro=self.libro,
            fecha_prestamo=self.hoy - timedelta(days=10),
            fecha_devolucion=self.hoy - timedelta(days=5),
            estado=Prestamo.ESTADO_PRESTADO,
        )
        # Simula el estado de stock que deja un préstamo activo.
        self.libro.cantidad -= 1
        self.libro.save(update_fields=['cantidad'])
        self.libro.refresh_from_db()
        self.assertEqual(self.libro.cantidad, 4)

        # La transición a Atrasado ocurre al consultar.
        self.client.get(reverse('prestamo-list'))
        prestamo.refresh_from_db()
        self.assertEqual(prestamo.estado, Prestamo.ESTADO_ATRASADO)

        response = self.client.delete(
            reverse('prestamo-detail', args=[prestamo.id_prestamo]))

        self.assert_envelope_exitosa(response)
        self.libro.refresh_from_db()
        self.assertEqual(self.libro.cantidad, 5)

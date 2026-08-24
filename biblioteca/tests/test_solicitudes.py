"""Tests para Solicitudes de Préstamo (RF-35).

Cubre: creación, aprobación (con validación de reglas), rechazo, cancelación,
y filtrado por rol en listados.
"""
from datetime import date, timedelta

from django.urls import reverse
from rest_framework.status import HTTP_403_FORBIDDEN

from biblioteca.models import Prestamo, SolicitudPrestamo
from biblioteca.tests.helpers import BaseAPITest


class SolicitudesTests(BaseAPITest):
    """Pruebas de solicitudes de préstamo."""

    def setUp(self):
        super().setUp()
        self.usuario = self.crear_usuario(email='solicitante@test.com')
        self.usuario2 = self.crear_usuario(email='otro@test.com')
        self.admin = self.crear_usuario(email='admin@test.com', role='admin')
        self.libro = self.crear_libro(titulo='Libro solicitado', isbn='978-3-16-148410-0', cantidad=5)
        self.hoy = date.today()

    def _crear_solicitud(self, usuario=None, libro=None, auth_as=None):
        if usuario is None:
            usuario = self.usuario
        if libro is None:
            libro = self.libro
        if auth_as is None:
            self.autenticar_como(usuario)
        payload = {'id_usuario': usuario.id, 'id_libro': libro.id_libro}
        response = self.client.post(reverse('solicitud-list'), payload, format='json')
        return response

    def test_usuario_crea_solicitud_para_si_mismo(self):
        """Un usuario normal puede crear solicitud para sí mismo."""
        self.autenticar_como(self.usuario)
        payload = {'id_libro': self.libro.id_libro}
        # No envía id_usuario (debe forzarse a sí mismo)
        response = self.client.post(reverse('solicitud-list'), payload, format='json')

        self.assert_envelope_exitosa(response, 201)
        data = response.data['datos']
        self.assertEqual(data['id_usuario'], self.usuario.id)
        self.assertEqual(data['id_libro'], self.libro.id_libro)
        self.assertEqual(data['estado'], SolicitudPrestamo.ESTADO_PENDIENTE)

    def test_usuario_no_puede_solicitar_para_otro(self):
        """Un usuario normal no puede solicitar para otro (se fuerza su propio id)."""
        self.autenticar_como(self.usuario)
        payload = {'id_usuario': self.usuario2.id, 'id_libro': self.libro.id_libro}
        response = self.client.post(reverse('solicitud-list'), payload, format='json')

        self.assert_envelope_exitosa(response, 201)
        data = response.data['datos']
        # Debe haber asignado el usuario autenticado, no el que se envió
        self.assertEqual(data['id_usuario'], self.usuario.id)

    def test_admin_puede_solicitar_para_cualquier_usuario(self):
        """Un admin puede crear solicitud para cualquier usuario."""
        self.autenticar_como(self.admin)
        payload = {'id_usuario': self.usuario.id, 'id_libro': self.libro.id_libro}
        response = self.client.post(reverse('solicitud-list'), payload, format='json')

        self.assert_envelope_exitosa(response, 201)
        data = response.data['datos']
        self.assertEqual(data['id_usuario'], self.usuario.id)

    def test_aprobar_solicitud_crea_prestamo(self):
        """Aprobar una solicitud válida crea un préstamo."""
        self.autenticar_como(self.usuario)
        create_resp = self._crear_solicitud()
        solicitud_id = create_resp.data['datos']['id_solicitud']

        self.autenticar_como(self.admin)
        response = self.client.post(
            reverse('solicitud-aprobar', args=[solicitud_id]),
            format='json'
        )

        self.assert_envelope_exitosa(response)
        data = response.data['datos']
        self.assertEqual(data['solicitud']['estado'], SolicitudPrestamo.ESTADO_APROBADA)
        self.assertIsNotNone(data['prestamo'])
        self.assertEqual(data['prestamo']['id_usuario'], self.usuario.id)
        self.assertEqual(data['prestamo']['id_libro'], self.libro.id_libro)
        self.assertEqual(data['prestamo']['estado'], Prestamo.ESTADO_PRESTADO)

        # Verificar que el préstamo se creó en la BD
        prestamos = Prestamo.objects.filter(id_usuario=self.usuario, id_libro=self.libro)
        self.assertEqual(prestamos.count(), 1)
        self.assertEqual(prestamos.first().fecha_vencimiento, self.hoy + timedelta(days=7))

    def test_aprobar_solicitud_con_stock_insuficiente(self):
        """No se puede aprobar si el libro no tiene disponibilidad."""
        # Ponemos el libro sin disponibilidad (creamos un préstamo activo que ocupa el único ejemplar)
        self.libro.cantidad = 1
        self.libro.save()
        prestamo = self.crear_prestamo(
            usuario=self.usuario2,
            libro=self.libro,
            fecha_prestamo=self.hoy,
            estado=Prestamo.ESTADO_PRESTADO,
        )
        self.assertEqual(self.libro.disponibles(), 0)

        self.autenticar_como(self.usuario)
        create_resp = self._crear_solicitud()
        solicitud_id = create_resp.data['datos']['id_solicitud']

        self.autenticar_como(self.admin)
        response = self.client.post(
            reverse('solicitud-aprobar', args=[solicitud_id]),
            format='json'
        )

        self.assert_envelope_error(response, 400)
        self.assertEqual(response.data['Mensaje'], 'No hay ejemplares disponibles de este libro')

    def test_aprobar_solicitud_con_usuario_vencido(self):
        """No se puede aprobar si el usuario tiene préstamos vencidos."""
        # Crear un préstamo vencido para el usuario
        self.crear_prestamo(
            usuario=self.usuario,
            libro=self.libro,
            fecha_prestamo=self.hoy - timedelta(days=10),
            fecha_devolucion=self.hoy - timedelta(days=5),
            estado=Prestamo.ESTADO_ATRASADO,
        )

        self.autenticar_como(self.usuario)
        create_resp = self._crear_solicitud()
        solicitud_id = create_resp.data['datos']['id_solicitud']

        self.autenticar_como(self.admin)
        response = self.client.post(
            reverse('solicitud-aprobar', args=[solicitud_id]),
            format='json'
        )

        self.assert_envelope_error(response, 400)
        self.assertEqual(
            response.data['Mensaje'],
            'El usuario tiene préstamos vencidos y no puede tomar nuevos préstamos'
        )

    def test_aprobar_solicitud_con_maximo_3_activos(self):
        """No se puede aprobar si el usuario ya tiene 3 préstamos activos."""
        # Crear 3 préstamos activos para el usuario
        for i in range(3):
            otro_libro = self.crear_libro(titulo=f'Libro {i}', isbn=f'978-{i}')
            self.crear_prestamo(
                usuario=self.usuario,
                libro=otro_libro,
                fecha_prestamo=self.hoy,
                estado=Prestamo.ESTADO_PRESTADO,
            )

        self.autenticar_como(self.usuario)
        create_resp = self._crear_solicitud()
        solicitud_id = create_resp.data['datos']['id_solicitud']

        self.autenticar_como(self.admin)
        response = self.client.post(
            reverse('solicitud-aprobar', args=[solicitud_id]),
            format='json'
        )

        self.assert_envelope_error(response, 400)
        self.assertEqual(
            response.data['Mensaje'],
            'El usuario ya tiene el máximo de 3 ejemplares prestados'
        )

    def test_rechazar_solicitud(self):
        """Rechazar una solicitud la marca como Rechazada."""
        self.autenticar_como(self.usuario)
        create_resp = self._crear_solicitud()
        solicitud_id = create_resp.data['datos']['id_solicitud']

        self.autenticar_como(self.admin)
        response = self.client.post(
            reverse('solicitud-rechazar', args=[solicitud_id]),
            format='json'
        )

        self.assert_envelope_exitosa(response)
        data = response.data['datos']
        self.assertEqual(data['estado'], SolicitudPrestamo.ESTADO_RECHAZADA)

    def test_cancelar_solicitud_por_usuario_dueño(self):
        """El usuario dueño puede cancelar su solicitud pendiente."""
        self.autenticar_como(self.usuario)
        create_resp = self._crear_solicitud()
        solicitud_id = create_resp.data['datos']['id_solicitud']

        response = self.client.post(
            reverse('solicitud-cancelar', args=[solicitud_id]),
            format='json'
        )

        self.assert_envelope_exitosa(response)
        data = response.data['datos']
        self.assertEqual(data['estado'], SolicitudPrestamo.ESTADO_CANCELADA)

    def test_cancelar_solicitud_por_otro_usuario_403(self):
        """Otro usuario no puede cancelar una solicitud que no le pertenece."""
        self.autenticar_como(self.usuario)
        create_resp = self._crear_solicitud()
        solicitud_id = create_resp.data['datos']['id_solicitud']

        self.autenticar_como(self.usuario2)
        response = self.client.post(
            reverse('solicitud-cancelar', args=[solicitud_id]),
            format='json'
        )

        self.assert_envelope_error(response, HTTP_403_FORBIDDEN)

    def test_usuario_normal_solo_ve_sus_solicitudes(self):
        """Un usuario normal en listado solo ve sus propias solicitudes."""
        self.autenticar_como(self.usuario)
        self._crear_solicitud()  # solicitud de usuario

        self.autenticar_como(self.usuario2)
        self._crear_solicitud()  # solicitud de usuario2

        # Usuario ve solo las suyas
        self.autenticar_como(self.usuario)
        response = self.client.get(reverse('solicitud-list'))
        self.assert_envelope_exitosa(response)
        data = response.data['datos']
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['id_usuario'], self.usuario.id)

    def test_admin_ve_todas_las_solicitudes(self):
        """Un admin ve todas las solicitudes."""
        self.autenticar_como(self.usuario)
        self._crear_solicitud()
        self.autenticar_como(self.usuario2)
        self._crear_solicitud()

        self.autenticar_como(self.admin)
        response = self.client.get(reverse('solicitud-list'))
        self.assert_envelope_exitosa(response)
        data = response.data['datos']
        self.assertEqual(len(data), 2)

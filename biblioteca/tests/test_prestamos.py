"""Cobertura de las reglas de negocio de Prestamos.

Verifica el manejo de stock (decisión (b): ``cantidad`` es el stock total
fijo y la disponibilidad se deriva de ``prestados()`` — no se decrementa al
prestar), el rechazo por falta de disponibilidad, la restitución de la
disponibilidad al devolver o eliminar un préstamo no devuelto, y la
transición automática Prestado -> Atrasado cuando el vencimiento ya pasó.
"""
from datetime import date, timedelta

from django.urls import reverse
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN

from biblioteca.models import Prestamo
from biblioteca.tests.helpers import BaseAPITest


class PrestamosReglasStockTests(BaseAPITest):
    """Reglas de negocio de stock en préstamos (DECISIÓN (b)).

    ``cantidad`` es el stock TOTAL (fijo) del libro y NUNCA cambia al
    prestar/devolver. La disponibilidad se deriva de los préstamos activos:
    disponibles = cantidad - prestados(). El stock físico no se decrementa al
    prestar, porque contar en ``prestados()`` Y además decrementar ``cantidad``
    sería doble conteo.
    """

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

    def test_prestar_no_decrementa_stock_total_sino_disponibilidad(self):
        response = self.crear_prestamo_via_api(fecha_devolucion=self.hoy + timedelta(days=7))

        self.assert_envelope_exitosa(response, 201)
        self.libro.refresh_from_db()
        self.assertEqual(self.libro.cantidad, 5)        # stock total NO cambia
        self.assertEqual(self.libro.disponibles(), 4)   # un ejemplar queda fuera

    def test_no_prestar_sin_disponibilidad(self):
        # RN-03: un solo ejemplar. El primer préstamo deja disponibilidad 0 y
        # el segundo debe rechazarse, sin doble conteo de stock (cantidad).
        librito = self.crear_libro(titulo='Dune 2', isbn='978-2', cantidad=1)
        respuesta = self.client.post(
            reverse('prestamo-list'),
            {'id_usuario': self.usuario.id,
             'id_libro': librito.id_libro,
             'fecha_prestamo': self.hoy.isoformat()},
            format='json',
        )
        self.assert_envelope_exitosa(respuesta, 201)
        librito.refresh_from_db()
        self.assertEqual(librito.disponibles(), 0)

        response = self.client.post(
            reverse('prestamo-list'),
            {'id_usuario': self.usuario.id,
             'id_libro': librito.id_libro,
             'fecha_prestamo': self.hoy.isoformat()},
            format='json',
        )

        self.assert_envelope_error(response, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['Mensaje'],
                         'No hay ejemplares disponibles de este libro')
        # El préstamo rechazado no se registró y la disponibilidad sigue en 0.
        self.assertEqual(Prestamo.objects.filter(id_libro=librito).count(), 1)
        librito.refresh_from_db()
        self.assertEqual(librito.disponibles(), 0)
        self.assertEqual(librito.cantidad, 1)  # stock total intacto

    def test_devolucion_recupera_disponibilidad(self):
        response = self.crear_prestamo_via_api(fecha_devolucion=self.hoy + timedelta(days=7))
        prestamo_id = response.data['datos']['id_prestamo']
        self.libro.refresh_from_db()
        self.assertEqual(self.libro.disponibles(), 4)

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
        self.assertEqual(self.libro.disponibles(), 5)
        self.assertEqual(self.libro.cantidad, 5)  # stock total intacto

    def test_eliminar_prestamo_no_devuelto_recupera_disponibilidad(self):
        response = self.crear_prestamo_via_api(fecha_devolucion=self.hoy + timedelta(days=7))
        prestamo_id = response.data['datos']['id_prestamo']
        self.libro.refresh_from_db()
        self.assertEqual(self.libro.disponibles(), 4)

        response = self.client.delete(
            reverse('prestamo-detail', args=[prestamo_id]))

        self.assert_envelope_exitosa(response)
        self.libro.refresh_from_db()
        self.assertEqual(self.libro.disponibles(), 5)
        self.assertEqual(self.libro.cantidad, 5)

    def test_eliminar_prestamo_devuelto_no_recupera_dos_veces(self):
        response = self.crear_prestamo_via_api(fecha_devolucion=self.hoy + timedelta(days=7))
        prestamo_id = response.data['datos']['id_prestamo']
        self.libro.refresh_from_db()
        self.assertEqual(self.libro.disponibles(), 4)

        # Devolver: la disponibilidad vuelve a 5.
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
        self.assertEqual(self.libro.disponibles(), 5)

        # Eliminar un préstamo ya devuelto no debe recuperar otra vez.
        response = self.client.delete(
            reverse('prestamo-detail', args=[prestamo_id]))
        self.assert_envelope_exitosa(response)
        self.libro.refresh_from_db()
        self.assertEqual(self.libro.disponibles(), 5)
        self.assertEqual(self.libro.cantidad, 5)

    def test_actualizar_prestamo_sin_cambiar_a_devuelto_no_afecta_disponibilidad(self):
        response = self.crear_prestamo_via_api(fecha_devolucion=self.hoy + timedelta(days=7))
        prestamo_id = response.data['datos']['id_prestamo']
        self.libro.refresh_from_db()
        self.assertEqual(self.libro.disponibles(), 4)

        # Actualización sin cambiar el estado: la disponibilidad no se mueve.
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
        self.assertEqual(self.libro.disponibles(), 4)
        self.assertEqual(self.libro.cantidad, 5)


class PrestamosMaximoSimultaneosTests(BaseAPITest):
    """RN-02 / RF-20: máximo 3 ejemplares simultáneos por usuario."""

    def setUp(self):
        super().setUp()
        self.usuario = self.crear_usuario(email='juan@test.com')
        self.libros = [
            self.crear_libro(titulo=f'Libro {i}', isbn=f'978-{i}', cantidad=5)
            for i in range(1, 5)
        ]
        self.hoy = date.today()

    def _prestar(self, libro):
        return self.client.post(
            reverse('prestamo-list'),
            {'id_usuario': self.usuario.id,
             'id_libro': libro.id_libro,
             'fecha_prestamo': self.hoy.isoformat()},
            format='json',
        )

    def test_permite_hasta_3_ejemplares_simultaneos(self):
        # Tres préstamos activos (uno por libro, con stock de sobra) es válido.
        for libro in self.libros[:3]:
            self.assert_envelope_exitosa(self._prestar(libro), 201)
        self.assertEqual(Prestamo.objects.count(), 3)
        self.assertEqual(
            Prestamo.objects.filter(id_usuario=self.usuario, estado__in=['Prestado', 'Atrasado']).count(),
            3,
        )

    def test_rechaza_el_cuarto_ejemplar_simultaneo(self):
        for libro in self.libros[:3]:
            self.assert_envelope_exitosa(self._prestar(libro), 201)

        response = self._prestar(self.libros[3])

        self.assert_envelope_error(response, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['Mensaje'],
                         'El usuario ya tiene el máximo de 3 ejemplares prestados')
        # El cuarto préstamo rechazado no se registró.
        self.assertEqual(Prestamo.objects.count(), 3)


class PrestamosBloqueoVencidosTests(BaseAPITest):
    """RN-04 / RF-25: bloqueo de nuevos préstamos si hay vencidos sin devolver."""

    def setUp(self):
        super().setUp()
        self.usuario = self.crear_usuario(email='juan@test.com')
        self.libro = self.crear_libro(titulo='Dune', isbn='978-1', cantidad=5)
        self.libro_nuevo = self.crear_libro(titulo='Otro', isbn='978-2', cantidad=5)
        self.hoy = date.today()

    def test_bloquea_nuevo_prestamo_si_usuario_tiene_vencido(self):
        # Un préstamo Atrasado (vencido y no devuelto) del mismo usuario.
        self.crear_prestamo(
            usuario=self.usuario,
            libro=self.libro,
            fecha_prestamo=self.hoy - timedelta(days=15),
            fecha_devolucion=self.hoy - timedelta(days=10),
            estado=Prestamo.ESTADO_ATRASADO,
        )

        response = self.client.post(
            reverse('prestamo-list'),
            {'id_usuario': self.usuario.id,
             'id_libro': self.libro_nuevo.id_libro,
             'fecha_prestamo': self.hoy.isoformat()},
            format='json',
        )

        self.assert_envelope_error(response, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['Mensaje'],
                         'El usuario tiene préstamos vencidos y no puede tomar nuevos préstamos')
        # No se registró ningún préstamo nuevo.
        self.assertEqual(Prestamo.objects.filter(id_usuario=self.usuario).count(), 1)

    def test_si_devuelve_el_vencido_puede_prestar(self):
        # Devolver el préstamo vencido (estado Devuelto) libera al usuario.
        vencido = self.crear_prestamo(
            usuario=self.usuario,
            libro=self.libro,
            fecha_prestamo=self.hoy - timedelta(days=15),
            fecha_devolucion=self.hoy - timedelta(days=10),
            estado=Prestamo.ESTADO_ATRASADO,
        )
        vencido.estado = Prestamo.ESTADO_DEVUELTO
        vencido.save(update_fields=['estado'])

        response = self.client.post(
            reverse('prestamo-list'),
            {'id_usuario': self.usuario.id,
             'id_libro': self.libro_nuevo.id_libro,
             'fecha_prestamo': self.hoy.isoformat()},
            format='json',
        )

        self.assert_envelope_exitosa(response, 201)


class PrestamosPermisosTests(BaseAPITest):
    """RN-05 / RFC-25: solo los administradores registran préstamos/devoluciones."""

    def setUp(self):
        super().setUp()
        self.usuario = self.crear_usuario(email='juan@test.com')
        self.admin = self.crear_usuario(email='admin@test.com', role='admin')
        self.libro = self.crear_libro(titulo='Dune', isbn='978-1', cantidad=5)
        self.hoy = date.today()

    def test_usuario_comun_no_puede_crear_prestamo(self):
        self.autenticar_como(self.usuario)
        response = self.client.post(
            reverse('prestamo-list'),
            {'id_usuario': self.usuario.id,
             'id_libro': self.libro.id_libro,
             'fecha_prestamo': self.hoy.isoformat()},
            format='json',
        )

        self.assert_envelope_error(response, HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['Mensaje'],
                         'No tiene permisos para realizar esta acción')
        self.assertEqual(Prestamo.objects.count(), 0)

    def test_usuario_comun_no_puede_devolver_ni_eliminar(self):
        prestamo = self.crear_prestamo(usuario=self.usuario, libro=self.libro)
        self.autenticar_como(self.usuario)

        # Devolución (update) rechazada.
        r = self.client.put(
            reverse('prestamo-detail', args=[prestamo.id_prestamo]),
            {'id_usuario': self.usuario.id,
             'id_libro': self.libro.id_libro,
             'fecha_prestamo': self.hoy.isoformat(),
             'estado': Prestamo.ESTADO_DEVUELTO},
            format='json',
        )
        self.assert_envelope_error(r, HTTP_403_FORBIDDEN)

        # Eliminación rechazada.
        r2 = self.client.delete(reverse('prestamo-detail', args=[prestamo.id_prestamo]))
        self.assert_envelope_error(r2, HTTP_403_FORBIDDEN)
        self.assertEqual(Prestamo.objects.count(), 1)

    def test_usuario_comun_si_puede_leer(self):
        # RN-05: la lectura (list) queda abierta a cualquier usuario autenticado.
        self.crear_prestamo(usuario=self.usuario, libro=self.libro)
        self.autenticar_como(self.usuario)

        response = self.client.get(reverse('prestamo-list'))

        self.assert_envelope_exitosa(response)
        self.assertEqual(len(response.data['datos']), 1)

    def test_admin_puede_crear(self):
        self.autenticar_como(self.admin)
        response = self.client.post(
            reverse('prestamo-list'),
            {'id_usuario': self.usuario.id,
             'id_libro': self.libro.id_libro,
             'fecha_prestamo': self.hoy.isoformat()},
            format='json',
        )

        self.assert_envelope_exitosa(response, 201)


class PrestamosDevolucionTests(BaseAPITest):
    """RF-22 / CU-12: registrar la fecha real de devolución y marcar si fue vencido."""

    def setUp(self):
        super().setUp()
        self.usuario = self.crear_usuario(email='juan@test.com')
        self.libro = self.crear_libro(titulo='Dune', isbn='978-1', cantidad=5)
        self.hoy = date.today()

    def _devolver(self, prestamo, fecha_prestamo, fecha_devolucion):
        # El admin autenticado (setUp base) registra la devolución (RN-05).
        return self.client.put(
            reverse('prestamo-detail', args=[prestamo.id_prestamo]),
            {'id_usuario': self.usuario.id,
             'id_libro': self.libro.id_libro,
             'fecha_prestamo': fecha_prestamo.isoformat(),
             'fecha_devolucion': fecha_devolucion.isoformat(),
             'estado': Prestamo.ESTADO_DEVUELTO},
            format='json',
        )

    def test_devolucion_en_plazo_guarda_fecha_real_y_no_vencido(self):
        # Vencimiento = fecha_prestamo + 7 = hoy + 4 (en el futuro): no está vencido.
        fecha_prestamo = self.hoy - timedelta(days=3)
        fecha_devolucion = self.hoy + timedelta(days=4)
        prestamo = self.crear_prestamo(
            usuario=self.usuario, libro=self.libro,
            fecha_prestamo=fecha_prestamo, fecha_devolucion=fecha_devolucion,
            estado=Prestamo.ESTADO_PRESTADO,
        )

        response = self._devolver(prestamo, fecha_prestamo, fecha_devolucion)

        self.assert_envelope_exitosa(response)
        prestamo.refresh_from_db()
        self.assertEqual(prestamo.estado, Prestamo.ESTADO_DEVUELTO)
        self.assertEqual(prestamo.fecha_devolucion_real, self.hoy)
        self.assertFalse(prestamo.devuelto_vencido)

    def test_devolucion_vencida_marca_devuelto_vencido(self):
        # Préstamo vencido (Atrasado) que se devuelve tarde: se marca el flag.
        fecha_prestamo = self.hoy - timedelta(days=15)
        fecha_devolucion = self.hoy - timedelta(days=10)  # límite del préstamo
        prestamo = self.crear_prestamo(
            usuario=self.usuario, libro=self.libro,
            fecha_prestamo=fecha_prestamo, fecha_devolucion=fecha_devolucion,
            estado=Prestamo.ESTADO_PRESTADO,
        )

        response = self._devolver(prestamo, fecha_prestamo, fecha_devolucion)

        self.assert_envelope_exitosa(response)
        prestamo.refresh_from_db()
        self.assertEqual(prestamo.estado, Prestamo.ESTADO_DEVUELTO)
        self.assertEqual(prestamo.fecha_devolucion_real, self.hoy)
        self.assertTrue(prestamo.devuelto_vencido)


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
        # Un préstamo vencido (Atrasado) mantiene el ejemplar fuera de la
        # disponibilidad (prestados() lo incluye); al eliminarlo, la
        # disponibilidad debe restituirse. El stock total (cantidad) NO cambia
        # (decisión (b)).
        prestamo = self.crear_prestamo(
            usuario=self.usuario,
            libro=self.libro,
            fecha_prestamo=self.hoy - timedelta(days=10),
            fecha_devolucion=self.hoy - timedelta(days=5),
            estado=Prestamo.ESTADO_PRESTADO,
        )
        # Un ejemplar queda fuera del catálogo por el préstamo activo.
        self.libro.refresh_from_db()
        self.assertEqual(self.libro.cantidad, 5)
        self.assertEqual(self.libro.disponibles(), 4)

        # La transición a Atrasado ocurre al consultar.
        self.client.get(reverse('prestamo-list'))
        prestamo.refresh_from_db()
        self.assertEqual(prestamo.estado, Prestamo.ESTADO_ATRASADO)

        response = self.client.delete(
            reverse('prestamo-detail', args=[prestamo.id_prestamo]))

        self.assert_envelope_exitosa(response)
        self.libro.refresh_from_db()
        self.assertEqual(self.libro.disponibles(), 5)
        self.assertEqual(self.libro.cantidad, 5)

from datetime import date, timedelta

from django.db import transaction
from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_403_FORBIDDEN
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema

from ..models import SolicitudPrestamo, Prestamo, Libro
from ..services.response import Result
from .serializers import (
    SolicitudPrestamoSerializer,
    SolicitudPrestamoCreateSerializer,
    SolicitudPrestamoUpdateEstadoSerializer,
)


def _permiso_escritura_solicitudes(request):
    """Misma lógica de protección por rol que en préstamos/reportes."""
    return request.user.role == 'admin' or request.user.is_staff


@extend_schema(tags=['solicitudes'])
class SolicitudPrestamoViewSet(viewsets.ModelViewSet):
    queryset = SolicitudPrestamo.objects.all()
    serializer_class = SolicitudPrestamoSerializer
    http_method_names = ['get', 'post', 'put', 'delete']

    def get_queryset(self):
        """Filtro por rol: USR ve solo sus solicitudes; ADM ve todas."""
        qs = SolicitudPrestamo.objects.all()
        if not _permiso_escritura_solicitudes(self.request):
            qs = qs.filter(id_usuario=self.request.user)
        return qs

    @extend_schema(
        description='Crear una solicitud de préstamo (RF-35).',
        request=SolicitudPrestamoCreateSerializer,
        responses={201: SolicitudPrestamoSerializer, 400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT},
    )
    def create(self, request):
        # Si es USR normal, fuerza su propio id_usuario
        id_usuario = request.data.get('id_usuario')
        if not _permiso_escritura_solicitudes(request):
            # Usuario normal: solo puede solicitar para sí mismo
            id_usuario = request.user.id
        else:
            # Admin: puede solicitar para cualquier usuario, pero debe existir
            if not id_usuario:
                return Result.Error("Debe indicar id_usuario", 400)

        # Validar que el usuario existe (si es admin y envía un id)
        from ..models import Usuario
        try:
            usuario = Usuario.objects.get(pk=id_usuario)
        except Usuario.DoesNotExist:
            return Result.Error("Usuario no encontrado", 400)

        id_libro = request.data.get('id_libro')
        if not id_libro:
            return Result.Error("Debe indicar id_libro", 400)

        try:
            libro = Libro.objects.get(pk=id_libro)
        except Libro.DoesNotExist:
            return Result.Error("Libro no encontrado", 400)

        if not libro.activo:
            return Result.Error("El libro no está disponible para solicitar", 400)

        # Crear la solicitud
        data = {
            'id_usuario': usuario.id,
            'id_libro': libro.id_libro,
            'observaciones': request.data.get('observaciones', ''),
        }
        serializer = SolicitudPrestamoCreateSerializer(data=data)
        if not serializer.is_valid():
            return Result.Error(serializer.errors, 400)

        solicitud = serializer.save()
        # Devolver con el serializer de lectura
        out_serializer = SolicitudPrestamoSerializer(solicitud)
        return Result.Exitosa("Solicitud creada correctamente", out_serializer.data, HTTP_201_CREATED)

    @extend_schema(
        description='Aprobar una solicitud de préstamo (solo ADM).',
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    @action(detail=True, methods=['post'], url_path='aprobar')
    def aprobar(self, request, pk=None):
        if not _permiso_escritura_solicitudes(request):
            return Result.Error("No tiene permisos para aprobar solicitudes", HTTP_403_FORBIDDEN)

        try:
            solicitud = SolicitudPrestamo.objects.get(pk=pk)
        except SolicitudPrestamo.DoesNotExist:
            return Result.Error("Solicitud no encontrada", 404)

        if solicitud.estado != SolicitudPrestamo.ESTADO_PENDIENTE:
            return Result.Error(
                f"La solicitud ya está {solicitud.estado.lower()} y no puede aprobarse",
                400
            )

        usuario = solicitud.id_usuario
        libro = solicitud.id_libro

        # Validar reglas de préstamo (RN-01/02/03/04)
        # RN-04: bloqueo por vencidos
        if Prestamo.objects.filter(id_usuario=usuario, estado='Atrasado').exists():
            return Result.Error(
                "El usuario tiene préstamos vencidos y no puede tomar nuevos préstamos",
                400
            )

        # RN-03: disponibilidad real
        if libro.disponibles() <= 0:
            return Result.Error(
                "No hay ejemplares disponibles de este libro",
                400
            )

        # RN-02: máx 3 activos
        activos = Prestamo.objects.filter(
            id_usuario=usuario,
            estado__in=['Prestado', 'Atrasado'],
        ).count()
        if activos >= 3:
            return Result.Error(
                "El usuario ya tiene el máximo de 3 ejemplares prestados",
                400
            )

        # RN-01: crear el préstamo con fecha_vencimiento = hoy + 7 días
        hoy = date.today()
        with transaction.atomic():
            prestamo = Prestamo.objects.create(
                id_usuario=usuario,
                id_libro=libro,
                fecha_prestamo=hoy,
                fecha_vencimiento=hoy + timedelta(days=7),
                estado=Prestamo.ESTADO_PRESTADO,
            )
            # Actualizar la solicitud
            solicitud.estado = SolicitudPrestamo.ESTADO_APROBADA
            solicitud.fecha_respuesta = hoy
            solicitud.save(update_fields=['estado', 'fecha_respuesta'])

        # Devolver el préstamo creado
        from ..prestamos.serializers import PrestamoSerializer
        prestamo_serializer = PrestamoSerializer(prestamo)
        return Result.Exitosa(
            "Solicitud aprobada y préstamo creado",
            {
                'solicitud': SolicitudPrestamoSerializer(solicitud).data,
                'prestamo': prestamo_serializer.data,
            },
            HTTP_200_OK,
        )

    @extend_schema(
        description='Rechazar una solicitud de préstamo (solo ADM).',
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    @action(detail=True, methods=['post'], url_path='rechazar')
    def rechazar(self, request, pk=None):
        if not _permiso_escritura_solicitudes(request):
            return Result.Error("No tiene permisos para rechazar solicitudes", HTTP_403_FORBIDDEN)

        try:
            solicitud = SolicitudPrestamo.objects.get(pk=pk)
        except SolicitudPrestamo.DoesNotExist:
            return Result.Error("Solicitud no encontrada", 404)

        if solicitud.estado != SolicitudPrestamo.ESTADO_PENDIENTE:
            return Result.Error(
                f"La solicitud ya está {solicitud.estado.lower()} y no puede rechazarse",
                400
            )

        solicitud.estado = SolicitudPrestamo.ESTADO_RECHAZADA
        solicitud.fecha_respuesta = date.today()
        solicitud.save(update_fields=['estado', 'fecha_respuesta'])

        serializer = SolicitudPrestamoSerializer(solicitud)
        return Result.Exitosa("Solicitud rechazada", serializer.data, HTTP_200_OK)

    @extend_schema(
        description='Cancelar una solicitud de préstamo (USR dueño o ADM).',
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    @action(detail=True, methods=['post'], url_path='cancelar')
    def cancelar(self, request, pk=None):
        try:
            solicitud = SolicitudPrestamo.objects.get(pk=pk)
        except SolicitudPrestamo.DoesNotExist:
            return Result.Error("Solicitud no encontrada", 404)

        # Solo el dueño o un admin pueden cancelar
        es_admin = _permiso_escritura_solicitudes(request)
        es_dueño = solicitud.id_usuario.id == request.user.id
        if not (es_admin or es_dueño):
            return Result.Error("No tiene permisos para cancelar esta solicitud", HTTP_403_FORBIDDEN)

        if solicitud.estado != SolicitudPrestamo.ESTADO_PENDIENTE:
            return Result.Error(
                f"La solicitud ya está {solicitud.estado.lower()} y no puede cancelarse",
                400
            )

        solicitud.estado = SolicitudPrestamo.ESTADO_CANCELADA
        solicitud.fecha_respuesta = date.today()
        solicitud.save(update_fields=['estado', 'fecha_respuesta'])

        serializer = SolicitudPrestamoSerializer(solicitud)
        return Result.Exitosa("Solicitud cancelada", serializer.data, HTTP_200_OK)

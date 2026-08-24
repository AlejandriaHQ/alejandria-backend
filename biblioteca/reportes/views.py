from datetime import date, datetime

from django.db.models import Count
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN

from ..models import Prestamo, Libro, Usuario
from ..services.response import Result


# PROTECCIÓN DE LECTURA (roles) — RF-26..RF-31 / CU-15: los reportes exponen
# métricas y deuda de la biblioteca, por lo que SOLO un usuario con
# role=='admin' (o is_staff) puede consultarlos. Se reutiliza la MISMA lógica
# que la protección de escritura de préstamos (_permiso_escritura_prestamos)
# para mantener un único criterio de acceso de administrador en todo el API.
# Al igual que en préstamos, se implementa con lógica en la vista (no con
# permission_classes de DRF) para preservar el envelope JSON
# {success, Mensaje, datos} coherente con el resto del backend.
def _permiso_escritura_reportes(request):
    return request.user.role == 'admin' or request.user.is_staff


@extend_schema(tags=['reportes'])
class ReportesViewSet(viewsets.ViewSet):
    """ViewSet de solo lectura con los reportes de la biblioteca (RF-26 a RF-31).

    Cada acción verifica el rol de administrador antes de consultar; los
    reportes nunca escriben sobre los modelos existentes.
    """

    # ------------------------------------------------------------------ #
    # RF-26 / CU-15 — Panel de indicadores generales
    # ------------------------------------------------------------------ #
    @extend_schema(
        description="Indicadores generales del panel (RF-26 / CU-15). Solo administradores.",
        responses={200: dict, 403: dict})
    @action(detail=False, methods=['get'], url_path='dashboard')
    def dashboard(self, request):
        if not _permiso_escritura_reportes(request):
            return Result.Error("No tiene permisos para ver reportes", HTTP_403_FORBIDDEN)

        desde_mes = date.today().replace(day=1)
        datos = {
            'total_libros': Libro.objects.count(),
            'total_usuarios': Usuario.objects.count(),
            'prestamos_activos': Prestamo.objects.filter(
                estado__in=[Prestamo.ESTADO_PRESTADO, Prestamo.ESTADO_ATRASADO]
            ).count(),
            'vencidos': Prestamo.objects.filter(estado=Prestamo.ESTADO_ATRASADO).count(),
            'prestamos_del_mes': Prestamo.objects.filter(
                fecha_prestamo__gte=desde_mes
            ).count(),
        }
        return Result.Exitosa("Indicadores del panel obtenidos correctamente", datos)

    # ------------------------------------------------------------------ #
    # RF-27 — Préstamos en un rango de fechas
    # ------------------------------------------------------------------ #
    @extend_schema(
        description="Préstamos cuyo fecha_prestamo está en el rango [desde, hasta] inclusive (RF-27). Solo administradores.",
        responses={200: dict, 400: dict, 403: dict})
    @action(detail=False, methods=['get'], url_path='prestamos')
    def prestamos(self, request):
        if not _permiso_escritura_reportes(request):
            return Result.Error("No tiene permisos para ver reportes", HTTP_403_FORBIDDEN)

        desde_raw = request.GET.get('desde')
        hasta_raw = request.GET.get('hasta')
        if not desde_raw or not hasta_raw:
            return Result.Error(
                "Debe indicar las fechas 'desde' y 'hasta' (formato AAAA-MM-DD)",
                HTTP_400_BAD_REQUEST,
            )
        try:
            desde = datetime.strptime(desde_raw, '%Y-%m-%d').date()
            hasta = datetime.strptime(hasta_raw, '%Y-%m-%d').date()
        except ValueError:
            return Result.Error(
                "Formato de fecha inválido. Use AAAA-MM-DD",
                HTTP_400_BAD_REQUEST,
            )

        qs = Prestamo.objects.filter(
            fecha_prestamo__gte=desde, fecha_prestamo__lte=hasta
        )
        prestamos = [
            {
                'id_prestamo': p.id_prestamo,
                'id_usuario': p.id_usuario_id,
                'id_libro': p.id_libro_id,
                'fecha_prestamo': p.fecha_prestamo.isoformat(),
                'estado': p.estado,
            }
            for p in qs
        ]
        datos = {
            'total': qs.count(),
            'rango': {'desde': desde.isoformat(), 'hasta': hasta.isoformat()},
            'prestamos': prestamos,
        }
        return Result.Exitosa("Reporte de préstamos por rango obtenido correctamente", datos)

    # ------------------------------------------------------------------ #
    # RF-28 — Devoluciones reales en un rango de fechas
    # ------------------------------------------------------------------ #
    @extend_schema(
        description="Devoluciones reales (fecha_devolucion_real) en el rango [desde, hasta] inclusive (RF-28). Solo administradores.",
        responses={200: dict, 400: dict, 403: dict})
    @action(detail=False, methods=['get'], url_path='devoluciones')
    def devoluciones(self, request):
        if not _permiso_escritura_reportes(request):
            return Result.Error("No tiene permisos para ver reportes", HTTP_403_FORBIDDEN)

        desde_raw = request.GET.get('desde')
        hasta_raw = request.GET.get('hasta')
        if not desde_raw or not hasta_raw:
            return Result.Error(
                "Debe indicar las fechas 'desde' y 'hasta' (formato AAAA-MM-DD)",
                HTTP_400_BAD_REQUEST,
            )
        try:
            desde = datetime.strptime(desde_raw, '%Y-%m-%d').date()
            hasta = datetime.strptime(hasta_raw, '%Y-%m-%d').date()
        except ValueError:
            return Result.Error(
                "Formato de fecha inválido. Use AAAA-MM-DD",
                HTTP_400_BAD_REQUEST,
            )

        qs = Prestamo.objects.filter(
            fecha_devolucion_real__gte=desde, fecha_devolucion_real__lte=hasta
        )
        devoluciones = [
            {
                'id_prestamo': p.id_prestamo,
                'id_usuario': p.id_usuario_id,
                'id_libro': p.id_libro_id,
                'fecha_devolucion_real': p.fecha_devolucion_real.isoformat(),
                'estado': p.estado,
            }
            for p in qs
        ]
        datos = {
            'total': qs.count(),
            'rango': {'desde': desde.isoformat(), 'hasta': hasta.isoformat()},
            'devoluciones': devoluciones,
        }
        return Result.Exitosa("Reporte de devoluciones por rango obtenido correctamente", datos)

    # ------------------------------------------------------------------ #
    # RF-29 — Inventario (cantidad, prestados, disponibles) por categoría
    # ------------------------------------------------------------------ #
    @extend_schema(
        description="Inventario de libros con cantidad, préstamos activos y disponibles por categoría (RF-29). Solo administradores.",
        responses={200: dict, 403: dict})
    @action(detail=False, methods=['get'], url_path='inventario')
    def inventario(self, request):
        if not _permiso_escritura_reportes(request):
            return Result.Error("No tiene permisos para ver reportes", HTTP_403_FORBIDDEN)

        libros = Libro.objects.select_related('id_categoria').all()
        datos = [
            {
                'categoria': libro.id_categoria.nombre if libro.id_categoria else None,
                'libro': libro.titulo,
                'cantidad': libro.cantidad,
                'prestados': libro.prestados(),
                'disponibles': libro.disponibles(),
            }
            for libro in libros
        ]
        return Result.Exitosa("Reporte de inventario obtenido correctamente", datos)

    # ------------------------------------------------------------------ #
    # RF-30 — Top libros más prestados
    # ------------------------------------------------------------------ #
    @extend_schema(
        description="Top 10 de libros más prestados (RF-30). Solo administradores.",
        responses={200: dict, 403: dict})
    @action(detail=False, methods=['get'], url_path='top-libros')
    def top_libros(self, request):
        if not _permiso_escritura_reportes(request):
            return Result.Error("No tiene permisos para ver reportes", HTTP_403_FORBIDDEN)

        agregacion = (
            Prestamo.objects.values('id_libro')
            .annotate(total=Count('id_prestamo'))
            .order_by('-total')[:10]
        )
        ids = [item['id_libro'] for item in agregacion]
        libros = {l.id_libro: l for l in Libro.objects.filter(pk__in=ids)}
        datos = [
            {
                'id_libro': item['id_libro'],
                'titulo': libros[item['id_libro']].titulo if item['id_libro'] in libros else None,
                'total_prestamos': item['total'],
            }
            for item in agregacion
        ]
        return Result.Exitosa("Top libros más prestados obtenido correctamente", datos)

    # ------------------------------------------------------------------ #
    # RF-31 — Top usuarios con más préstamos
    # ------------------------------------------------------------------ #
    @extend_schema(
        description="Top 10 de usuarios con más préstamos (RF-31). Solo administradores.",
        responses={200: dict, 403: dict})
    @action(detail=False, methods=['get'], url_path='top-usuarios')
    def top_usuarios(self, request):
        if not _permiso_escritura_reportes(request):
            return Result.Error("No tiene permisos para ver reportes", HTTP_403_FORBIDDEN)

        agregacion = (
            Prestamo.objects.values('id_usuario')
            .annotate(total=Count('id_prestamo'))
            .order_by('-total')[:10]
        )
        ids = [item['id_usuario'] for item in agregacion]
        usuarios = {u.id: u for u in Usuario.objects.filter(pk__in=ids)}
        datos = [
            {
                'id_usuario': item['id_usuario'],
                'nombre': usuarios[item['id_usuario']].get_full_name() if item['id_usuario'] in usuarios else '',
                'email': usuarios[item['id_usuario']].email if item['id_usuario'] in usuarios else '',
                'total_prestamos': item['total'],
            }
            for item in agregacion
        ]
        return Result.Exitosa("Top usuarios con más préstamos obtenido correctamente", datos)

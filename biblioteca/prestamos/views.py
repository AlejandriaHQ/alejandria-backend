from datetime import date

from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q, ProtectedError
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter

from ..models import Prestamo, Libro
from ..services.response import Result
from .serializers import (
    PrestamoSerializer,
    PrestamoSerializerReg,
    PrestamoSerializerUpdate,
    PrestamoSerializerDelete,
)


def _obtener_o_none(queryset, pk):
    """Devuelve el registro por pk, o None si no existe o el pk no es numérico.

    Un pk no numérico (p.ej. /prestamos/abc/) lanza ValueError al filtrar
    sobre un AutoField; se captura para que el ViewSet responda 404 con el
    envelope en lugar de un 500 (F03 pentest).
    """
    try:
        return queryset.filter(pk=pk).first()
    except (ValueError, TypeError):
        return None


page_paramView = OpenApiParameter(
    'page',
    OpenApiTypes.INT,
    OpenApiParameter.QUERY,
    description="Page",
)

filter_paramView = OpenApiParameter(
    'filter',
    OpenApiTypes.STR,
    OpenApiParameter.QUERY,
    description="Filter",
)


def _normalizar_atrasados():
    # Transición automática Prestado -> Atrasado: se actualiza en masa antes
    # de devolver los datos. La fecha canónica de vencimiento es
    # fecha_vencimiento; para registros creados fuera del serializer (sin
    # fecha_vencimiento) se cae a fecha_devolucion como límite histórico.
    # NO afecta el stock: solo Prestado -> Devuelto devuelve ejemplares; un
    # préstamo Atrasado mantiene el ejemplar fuera del stock hasta que se
    # devuelva.
    hoy = date.today()
    Prestamo.objects.filter(estado='Prestado').filter(
        Q(fecha_vencimiento__isnull=False, fecha_vencimiento__lt=hoy) |
        Q(fecha_vencimiento__isnull=True, fecha_devolucion__isnull=False, fecha_devolucion__lt=hoy)
    ).update(estado='Atrasado')


# RN-02 / RF-20: número máximo de ejemplares prestados simultáneamente a un
# mismo socio. Se cuenta sobre préstamos ACTIVOS (Prestado o Atrasado): los
# devueltos no ocupan cuota.
MAX_PRESTAMOS_SIMULTANEOS = 3


@extend_schema(tags=['prestamos'])
class PrestamoViewSet(viewsets.ModelViewSet):
    queryset = Prestamo.objects.all()
    serializer_class = PrestamoSerializer
    http_method_names = ['get', 'post', 'put', 'delete']

    @extend_schema(
        description="Obtener la lista de préstamos",
        responses={200: OpenApiTypes.OBJECT})
    def list(self, request):
        _normalizar_atrasados()
        prestamos = Prestamo.objects.all()
        serializer = PrestamoSerializerReg(prestamos, many=True)
        return Result.Exitosa("Lista de préstamos obtenida correctamente", serializer.data)

    @extend_schema(
        description='Añade un nuevo prestamo.',
        request=PrestamoSerializerReg,
        responses={201: PrestamoSerializerReg, 400: OpenApiTypes.OBJECT})
    def create(self, request):
        id_usuario = request.data.get('id_usuario')
        id_libro = request.data.get('id_libro')
        fecha_prestamo = request.data.get('fecha_prestamo')

        errores = []
        if not id_usuario:
            errores.append("Complete la casilla id_usuario")
        if not id_libro:
            errores.append("Complete la casilla id_libro")
        if not fecha_prestamo:
            errores.append("Complete la casilla fecha_prestamo")

        if errores:
            return Result.Error(errores)

        serialData = PrestamoSerializerReg(data=request.data)

        if serialData.is_valid():
            try:
                # Regla de stock (DECISIÓN (b)): `cantidad` es el STOCK TOTAL
                # (fijo) del libro y NUNCA cambia al prestar/devolver. La
                # disponibilidad se DERIVA de los préstamos activos:
                # disponibles = cantidad - prestados(). Por eso aquí solo se
                # valida la disponibilidad real dentro de una transacción
                # atómica (select_for_update bloquea la fila del libro para
                # evitar condiciones de carrera) y NO se decrementa cantidad.
                with transaction.atomic():
                    libro = Libro.objects.select_for_update().get(pk=id_libro)

                    if libro.disponibles() <= 0:
                        return Result.Error("No hay ejemplares disponibles de este libro", 400)

                    # RN-02 / RF-20: máximo de 3 ejemplares simultáneos por usuario.
                    # Se cuentan los préstamos ACTIVOS (Prestado/Atrasado); los
                    # devueltos no ocupan cuota.
                    activos = Prestamo.objects.filter(
                        id_usuario_id=id_usuario,
                        estado__in=['Prestado', 'Atrasado'],
                    ).count()
                    if activos >= MAX_PRESTAMOS_SIMULTANEOS:
                        return Result.Error("El usuario ya tiene el máximo de 3 ejemplares prestados", 400)

                    serialData.save()
            except IntegrityError:
                return Result.Error("Ya existe un registro con ese valor único", 400)
        else:
            # Se devuelven los errores del serializer (p. ej. fecha de préstamo
            # fuera de rango) en lugar del mensaje genérico y engañoso;
            # mismo patrón que libros y usuarios.
            return Result.Error(serialData.errors)

        return Result.Exitosa("Se registro correctamente", serialData.data, HTTP_201_CREATED)

    @extend_schema(
        description="Obtener un prestamo por su ID",
        responses={200: PrestamoSerializer, 404: OpenApiTypes.OBJECT})
    def retrieve(self, request, pk=None):
        _normalizar_atrasados()
        prestamo = _obtener_o_none(Prestamo.objects, pk)
        if not prestamo:
            return Result.Error("Registro no encontrado", 404)

        serialData = PrestamoSerializer(prestamo)
        return Result.Exitosa("", serialData.data, HTTP_200_OK)

    @extend_schema(
        description="Actualiza un prestamo.",
        request=PrestamoSerializerUpdate,
        responses={200: PrestamoSerializerUpdate, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT})
    def update(self, request, pk=None):
        # Transición automática Prestado -> Atrasado: se aplica también en update
        # para que un préstamo vencido muestre su estado consistente tras editarse.
        _normalizar_atrasados()

        id_usuario = request.data.get('id_usuario')
        id_libro = request.data.get('id_libro')
        fecha_prestamo = request.data.get('fecha_prestamo')

        errores = []
        if not id_usuario:
            errores.append("Complete la casilla id_usuario")

        if not id_libro:
            errores.append("Complete la casilla id_libro")

        if not fecha_prestamo:
            errores.append("Complete la casilla fecha_prestamo")

        if errores:
            return Result.Error(errores)

        prestamo = _obtener_o_none(Prestamo.objects, pk)
        if not prestamo:
            return Result.Error("Registro no encontrado", 404)

        serialData = PrestamoSerializerUpdate(instance=prestamo, data=request.data)

        if serialData.is_valid():
            try:
                with transaction.atomic():
                    serialData.save()
                    # Regla de stock (DECISIÓN (b)): NO se ajusta `cantidad` al
                    # actualizar. La disponibilidad se deriva de los préstamos
                    # activos (prestados()), por lo que al pasar a Devuelto el
                    # ejemplar vuelve a estar disponible automáticamente (el
                    # contador prestados() deja de incluirlo), sin tocar stock.
            except IntegrityError:
                return Result.Error("Ya existe un registro con ese valor único", 400)
        else:
            # Se devuelven los errores del serializer (p. ej. fecha de préstamo
            # fuera de rango) en lugar del mensaje genérico y engañoso;
            # mismo patrón que libros y usuarios.
            return Result.Error(serialData.errors)

        return Result.Exitosa("Se actualizo correctamente", serialData.data, HTTP_200_OK)

    @extend_schema(
        description="Eliminar un prestamo",
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT})
    def destroy(self, request, pk=None):
        # Transición automática Prestado -> Atrasado: se aplica también en delete
        # para mantener el estado consistente antes de eliminar.
        _normalizar_atrasados()

        prestamo = _obtener_o_none(Prestamo.objects, pk)
        if not prestamo:
            return Result.Error("Registro no encontrado", 404)

        # Regla de stock (DECISIÓN (b)): NO se ajusta `cantidad` al eliminar.
        # Al borrar un préstamo activo (Prestado/Atrasado) el contador
        # prestados() deja de incluirlo, por lo que la disponibilidad se
        # recupera automáticamente sin tocar el stock total.
        try:
            prestamo.delete()
        except ProtectedError:
            return Result.Error("No se puede eliminar el prestamo")

        return Result.Exitosa("Se elimino correctamente", {}, HTTP_200_OK)

    @extend_schema(
        description="Buscar",
        parameters=[page_paramView, filter_paramView],
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT})
    @action(detail=False, methods=['get'], url_path='paginar')
    def paginar(self, request):
        page = request.GET.get('page')
        pagesize = 10
        filter = request.GET.get('filter')

        # Transición automática Prestado -> Atrasado sobre préstamos vencidos
        _normalizar_atrasados()

        if filter:
            query = Q(estado__icontains=filter)

            cont = Prestamo.objects.filter(query).order_by('id_prestamo')

        else:
            cont = Prestamo.objects.all().order_by('id_prestamo')

        paginator = Paginator(cont, pagesize)
        total_pages = paginator.num_pages

        # F16 pentest: si page viene y no es un entero válido se responde 400
        # con el envelope (antes se degradaba silenciosamente a página 1);
        # si no viene, se usa la página 1.
        if page is None:
            page = 1
        else:
            try:
                page = int(page)
            except (ValueError, TypeError):
                return Result.Error("El parámetro page debe ser un número entero")

        if page > total_pages or page < 1:
            return Result.ErrorResponsePaginator("No se encuentra esta página", total_pages, page)

        page_obj = paginator.page(page)

        button_previous = page > 1
        button_next = page < total_pages

        serialdata = PrestamoSerializer(page_obj, many=True)

        return Result.ResponsePaginator('', serialdata.data, total_pages, page, button_previous, button_next)

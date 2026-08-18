from .serializersPrestamos import PrestamoSerializer, PrestamoSerializerReg, PrestamoSerializerUpdate, PrestamoSerializerDelete
from rest_framework.decorators import api_view
from biblioteca.models import Prestamo, Libro
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from django.db.models import Q, ProtectedError, F
from django.db import IntegrityError, transaction
from django.core.paginator import Paginator
from datetime import date
from ..services.response import Result, TryCatch

#Prestamos Views


@extend_schema(
    description="Obtener la lista de préstamos",
    responses={200: OpenApiTypes.OBJECT})

@api_view(['GET'])
def prestamos_list(request):
    def action_to_execute():
        # Transición automática Prestado -> Atrasado: se actualiza en masa antes
        # de devolver los datos (update_atrasados), sin afectar el stock.
        Prestamo.objects.filter(estado='Prestado', fecha_devolucion__lt=date.today()).update(estado='Atrasado')
        prestamos = Prestamo.objects.all()
        serializer = PrestamoSerializerReg(prestamos, many=True)
        return Result.Exitosa("Lista de préstamos obtenida correctamente", serializer.data)

    return TryCatch(action_to_execute)


pk_paramView = OpenApiParameter(
    'id_prestamo', OpenApiTypes.INT, OpenApiParameter.QUERY,
    description="ID del prestamo")


@extend_schema(
    description="Obtener un prestamo por su ID",
    parameters=[pk_paramView],
    responses={200: PrestamoSerializer(many=True), 404: OpenApiTypes.OBJECT})

@api_view(['GET'])
def Prestamo_View(request):
    id = request.GET.get('id_prestamo')
    if not id:
        return Result.Error("Complete la casilla del ID del prestamo")

    # Transición automática Prestado -> Atrasado sobre préstamos vencidos
    Prestamo.objects.filter(estado='Prestado', fecha_devolucion__lt=date.today()).update(estado='Atrasado')

    prestamo = Prestamo.objects.filter(id_prestamo=id)
    if not prestamo.exists():
        return Result.Error("Registro no encontrado", 404)

    serialData = PrestamoSerializer(prestamo, many=True)

    return Result.Exitosa("", serialData.data, HTTP_200_OK)


@extend_schema(
    description='Añade un nuevo prestamo.',
    request=PrestamoSerializerReg,
    responses={201: PrestamoSerializerReg, 400: OpenApiTypes.OBJECT})

@api_view(['POST'])
def Prestamo_Add(request):
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
            # Regla de stock: se valida disponibilidad y se decrementa el stock
            # de forma atómica dentro de una transacción (select_for_update bloquea
            # la fila del libro para evitar condiciones de carrera concurrentes).
            #
            # NOTA: no se captura Libro.DoesNotExist aquí. id_libro es un
            # PrimaryKeyRelatedField del serializer, por lo que un id inexistente
            # hace fallar is_valid() con 400 antes de llegar a este bloque; el
            # 400 de DRF ya cubre ese caso (código muerto eliminado).
            with transaction.atomic():
                libro = Libro.objects.select_for_update().get(pk=id_libro)

                if libro.cantidad < 1:
                    return Result.Error("No hay ejemplares disponibles de este libro", 400)

                serialData.save()
                # Decremento atómico del stock al prestar (nunca baja de 0 porque
                # ya se validó cantidad >= 1 dentro de la misma transacción).
                Libro.objects.filter(pk=id_libro).update(cantidad=F('cantidad') - 1)
        except IntegrityError:
            return Result.Error("Ya existe un registro con ese valor único", 400)
    else:
        return Result.Error("Complete los campos vacios")

    return Result.Exitosa("Se registro correctamente", serialData.data, HTTP_201_CREATED)


@extend_schema(
    description="Actualiza un prestamo.",
    request=PrestamoSerializerUpdate,
    responses={200: PrestamoSerializerUpdate, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT})

@api_view(['PUT'])
def Prestamo_Update(request):
    pk = request.data.get('id_prestamo')

    id_usuario = request.data.get('id_usuario')
    id_libro = request.data.get('id_libro')
    fecha_prestamo = request.data.get('fecha_prestamo')

    errores = []
    if not pk:
        errores.append("Complete la casilla del ID del prestamo")
    if not id_usuario:
        errores.append("Complete la casilla id_usuario")

    if not id_libro:
        errores.append("Complete la casilla id_libro")

    if not fecha_prestamo:
        errores.append("Complete la casilla fecha_prestamo")

    if errores:
        return Result.Error(errores)

    try:
        prestamo = Prestamo.objects.get(id_prestamo=pk)
    except Prestamo.DoesNotExist:
        return Result.Error("Registro no encontrado", 404)

    # Estado previo para decidir el ajuste de stock tras la actualización
    estado_anterior = prestamo.estado

    serialData = PrestamoSerializerUpdate(instance=prestamo, data=request.data)

    if serialData.is_valid():
        try:
            with transaction.atomic():
                serialData.save()
                # Regla de stock según el cambio de estado:
                #  - Pasa a Devuelto (antes no lo era): el ejemplar vuelve al stock.
                #  - Deja de estar Devuelto: el ejemplar vuelve a estar prestado,
                #    se decrementa (con guard para no bajar de 0).
                nuevo_estado = prestamo.estado  # tras save() el instance ya refleja el nuevo valor
                if estado_anterior != 'Devuelto' and nuevo_estado == 'Devuelto':
                    Libro.objects.filter(pk=prestamo.id_libro_id).update(cantidad=F('cantidad') + 1)
                elif estado_anterior == 'Devuelto' and nuevo_estado != 'Devuelto':
                    Libro.objects.filter(pk=prestamo.id_libro_id, cantidad__gt=0).update(cantidad=F('cantidad') - 1)
        except IntegrityError:
            return Result.Error("Ya existe un registro con ese valor único", 400)
    else:
        return Result.Error("Complete los campos vacios")

    return Result.Exitosa("Se actualizo correctamente", serialData.data, HTTP_200_OK)


pk_paramView = OpenApiParameter(
    'id_prestamo',
    OpenApiTypes.INT,
    OpenApiParameter.QUERY,
    description="ID del prestamo",
)


@extend_schema(
    description="Eliminar un prestamo",
    parameters=[pk_paramView],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT})

@api_view(['DELETE'])
def Prestamo_Delete(request):

    pk = request.GET.get('id_prestamo')
    if not pk:
        return Result.Error("Complete la casilla del ID del prestamo")

    try:
        prestamo = Prestamo.objects.get(id_prestamo=pk)
    except Prestamo.DoesNotExist:
        return Result.Error("Registro no encontrado", 404)

    # Regla de stock: si el préstamo aún no estaba devuelto (Prestado/Atrasado),
    # el ejemplar estaba fuera del stock, por lo que al eliminar se devuelve.
    if prestamo.estado != 'Devuelto':
        Libro.objects.filter(pk=prestamo.id_libro_id).update(cantidad=F('cantidad') + 1)

    try:
        prestamo.delete()
    except ProtectedError:
        return Result.Error("No se puede eliminar el prestamo")

    return Result.Exitosa("Se elimino correctamente", {}, HTTP_200_OK)


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


@extend_schema(
    description="Buscar",
    parameters=[page_paramView, filter_paramView],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT})

@api_view(['GET'])
def Prestamo_Paginators(request):
    page = request.GET.get('page')
    pagesize = 10
    filter = request.GET.get('filter')

    # Transición automática Prestado -> Atrasado sobre préstamos vencidos
    Prestamo.objects.filter(estado='Prestado', fecha_devolucion__lt=date.today()).update(estado='Atrasado')

    if filter:
        query = Q(estado__icontains=filter)

        cont = Prestamo.objects.filter(query).order_by('id_prestamo')

    else:
        cont = Prestamo.objects.all().order_by('id_prestamo')

    paginator = Paginator(cont, pagesize)
    total_pages = paginator.num_pages

    try:
        page = int(page)
    except (ValueError, TypeError):
        page = 1

    if page > total_pages or page < 1:
        return Result.ErrorResponsePaginator("No se encuentra esta página", total_pages, page)

    page_obj = paginator.page(page)

    button_previous = page > 1
    button_next = page < total_pages

    serialdata = PrestamoSerializer(page_obj, many=True)

    return Result.ResponsePaginator('', serialdata.data, total_pages, page, button_previous, button_next)

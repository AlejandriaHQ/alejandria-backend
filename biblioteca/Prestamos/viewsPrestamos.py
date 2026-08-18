from .serializersPrestamos import PrestamoSerializer, PrestamoSerializerReg, PrestamoSerializerUpdate, PrestamoSerializerDelete
from rest_framework.decorators import api_view
from biblioteca.models import Prestamo
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from django.db.models import Q, ProtectedError
from django.db import IntegrityError
from django.core.paginator import Paginator
from ..services.response import Result, TryCatch

#Prestamos Views


@extend_schema(
    description="Obtener la lista de préstamos",
    responses={200: OpenApiTypes.OBJECT})

@api_view(['GET'])
def prestamos_list(request):
    def action_to_execute():
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
            serialData.save()
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

    serialData = PrestamoSerializerUpdate(instance=prestamo, data=request.data)

    if serialData.is_valid():
        try:
            serialData.save()
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

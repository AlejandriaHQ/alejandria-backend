from .serializersPrestamos import PrestamoSerializer, PrestamoSerializerReg, PrestamoSerializerUpdate, PrestamoSerializerDelete
from rest_framework.decorators import api_view
from biblioteca.models import Prestamo
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db.models import Q, ProtectedError
from django.core.paginator import Paginator
from ..services.response import Result, TryCatch

#Prestamos Views


@api_view(['GET'])
def prestamos_list(request):
    def action_to_execute():
        prestamos = Prestamo.objects.all()
        serializer = PrestamoSerializerReg(prestamos, many=True)
        return Response(serializer.data, status=HTTP_200_OK)

    return TryCatch(action_to_execute)


pk_paramView = openapi.Parameter(
    'id_prestamo', openapi.IN_QUERY,
    description="ID del prestamo",
    type=openapi.TYPE_INTEGER)


@swagger_auto_schema(
    method='get', operation_description="Obtener un prestamo por su ID", manual_parameters=[pk_paramView], responses={200: 'Exitoso', 400: 'Error'})

@api_view(['GET'])
def Prestamo_View(request):
    id = request.GET.get('id_prestamo')
    if not id:
        return Result.Error("Complete la casilla del ID del prestamo")

    prestamo = Prestamo.objects.filter(id_prestamo=id)
    serialData = PrestamoSerializer(prestamo, many=True)

    return Result.Exitosa("", serialData.data, HTTP_200_OK)


@swagger_auto_schema(
    method='post',
    operation_description='Añade un nuevo prestamo.',
    request_body=PrestamoSerializerReg,
    responses={200: 'Exitoso', 400: 'Error'})

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
        serialData.save()
    else:
        return Result.Error("Complete los campos vacios")

    return Result.Exitosa("Se registro correctamente", serialData.data, HTTP_201_CREATED)


@swagger_auto_schema(
    method='put',
    operation_description="Actualiza un prestamo.",
    request_body=PrestamoSerializerUpdate,
    responses={200: 'Exitoso', 400: 'Error'})

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
        return Result.Error("El prestamo no existe")

    serialData = PrestamoSerializerUpdate(instance=prestamo, data=request.data)

    if serialData.is_valid():
        serialData.save()
    else:
        return Result.Error("Complete los campos vacios")

    return Result.Exitosa("Se actualizo correctamente", serialData.data, HTTP_200_OK)


pk_paramView = openapi.Parameter(
    'id_prestamo',
    openapi.IN_QUERY,
    description="ID del prestamo",
    type=openapi.TYPE_INTEGER,
)


@swagger_auto_schema(
    method='delete',
    operation_description="Eliminar un prestamo",
    manual_parameters=[pk_paramView],
    responses={200: 'Exitoso', 400: 'Error'})

@api_view(['DELETE'])
def Prestamo_Delete(request):

    pk = request.GET.get('id_prestamo')
    if not pk:
        return Result.Error("Complete la casilla del ID del prestamo")

    try:
        prestamo = Prestamo.objects.get(id_prestamo=pk)
    except Prestamo.DoesNotExist:
        return Result.Error("El prestamo no existe")

    try:
        prestamo.delete()
    except ProtectedError:
        return Result.Error("No se puede eliminar el prestamo")

    return Result.Exitosa("Se elimino correctamente", {}, HTTP_200_OK)


page_paramView = openapi.Parameter(
    'page',
    openapi.IN_QUERY,
    description="Page",
    type=openapi.TYPE_INTEGER,
)

filter_paramView = openapi.Parameter(
    'filter',
    openapi.IN_QUERY,
    description="Filter",
    type=openapi.TYPE_STRING,
)


@swagger_auto_schema(
    method='get',
    operation_description="Buscar",
    manual_parameters=[page_paramView, filter_paramView],
    responses={200: 'Exitoso', 400: 'Error'})

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

    if page == total_pages:
        button_previous = True
        button_next = False
    elif page <= 1:
        button_previous = False
        button_next = True
    else:
        button_previous = True
        button_next = True

    serialdata = PrestamoSerializer(page_obj, many=True)

    return Result.ResponsePaginator('', serialdata.data, total_pages, page, button_previous, button_next)

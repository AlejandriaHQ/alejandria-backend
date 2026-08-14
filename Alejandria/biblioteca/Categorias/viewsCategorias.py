from .serializersCategorias import CategoriasSerializer, CategoriasSerializerReg, CategoriasSerializerUpdate, CategoriasSerializerDelete
from rest_framework.decorators import api_view
from biblioteca.models import Categoria
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db.models import Q, ProtectedError
from django.core.paginator import Paginator
from ..services.response import Result, TryCatch

#Categorias Views


@api_view(['GET'])
def categorias_list(request):
    def action_to_execute():
        categorias = Categoria.objects.all()
        serializer = CategoriasSerializerReg(categorias, many=True)
        return Response(serializer.data, status=HTTP_200_OK)

    return TryCatch(action_to_execute)


pk_paramView = openapi.Parameter(
    'id_categoria',
    openapi.IN_QUERY,
    description="ID de la categoría",
    type=openapi.TYPE_INTEGER,
)


@swagger_auto_schema(
    method='get',
    operation_description="Obtener una categoría por su ID",
    manual_parameters=[pk_paramView],
    responses={200: 'Exitoso', 400: 'Error'})

@api_view(['GET'])
def Categoria_View(request):
    id = request.GET.get('id_categoria')
    if not id:
        return Result.Error("Complete la casilla del ID de la categoria")

    categoria = Categoria.objects.filter(id_categoria=id)
    serialData = CategoriasSerializer(categoria, many=True)

    return Result.Exitosa("", serialData.data, HTTP_200_OK)


@swagger_auto_schema(
    method='post',
    operation_description='Añade una nueva categoria.',
    request_body=CategoriasSerializerReg,
    responses={200: 'Exitoso', 400: 'Error'})

@api_view(['POST'])
def Categoria_Add(request):
    errores = []

    nombre = request.data.get('nombre')
    if not nombre:
        errores.append("Complete la casilla nombre")

    if errores:
        return Result.Error(errores)

    serialData = CategoriasSerializerReg(data=request.data)

    if not serialData.is_valid():
        return Result.Error("Complete los campos vacios")

    serialData.save()

    return Result.Exitosa("Se registro correctamente", serialData.data, HTTP_201_CREATED)


@swagger_auto_schema(
    method='put',
    operation_description="Actualiza una categoria.",
    request_body=CategoriasSerializerUpdate,
    responses={200: 'Exitoso', 400: 'Error'})

@api_view(['PUT'])
def Categoria_Update(request):
    errores = []

    pk = request.data.get('id_categoria')
    nombre = request.data.get('nombre')

    if not pk:
        errores.append("Complete la casilla del ID de la categoria")
    if not nombre:
        errores.append("Complete la casilla nombre")

    if errores:
        return Result.Error(errores)

    try:
        categoria = Categoria.objects.get(id_categoria=pk)
    except Categoria.DoesNotExist:
        return Result.Error("La categoria no existe")

    serialData = CategoriasSerializerUpdate(instance=categoria, data=request.data)

    if not serialData.is_valid():
        return Result.Error("Complete los campos vacios")

    serialData.save()

    return Result.Exitosa("Se actualizo correctamente", serialData.data, HTTP_200_OK)


@swagger_auto_schema(
    method='delete',
    operation_description="Eliminar un Categoria",
    manual_parameters=[pk_paramView],
    responses={200: 'Exitoso', 400: 'Error'})

@api_view(['DELETE'])
def Categoria_Delete(request):
    pk = request.GET.get('id_categoria')
    if not pk:
        return Result.Error("Complete la casilla del ID de la categoria")

    try:
        categoria = Categoria.objects.get(id_categoria=pk)
    except Categoria.DoesNotExist:
        return Result.Error("La categoria no existe")

    try:
        categoria.delete()
    except ProtectedError:
        return Result.Error("No se puede eliminar: la categoria tiene libros asociados")

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
def Categoria_Paginators(request):
    page = request.GET.get('page')
    pagesize = 10
    filter = request.GET.get('filter')

    if filter:
        query = Q(nombre__icontains=filter) | \
                Q(descripcion__icontains=filter)

        cont = Categoria.objects.filter(query).order_by('id_categoria')
    else:
        cont = Categoria.objects.all().order_by('id_categoria')

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

    serialdata = CategoriasSerializer(page_obj, many=True)

    return Result.ResponsePaginator('', serialdata.data, total_pages, page, button_previous, button_next)

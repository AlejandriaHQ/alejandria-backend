from .serializersCategorias import CategoriasSerializer, CategoriasSerializerReg, CategoriasSerializerUpdate, CategoriasSerializerDelete
from rest_framework.decorators import api_view
from biblioteca.models import Categoria
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from django.db.models import Q, ProtectedError
from django.core.paginator import Paginator
from ..services.response import Result, TryCatch

#Categorias Views


@extend_schema(
    description="Obtener la lista de categorías",
    responses={200: CategoriasSerializerReg(many=True)})

@api_view(['GET'])
def categorias_list(request):
    def action_to_execute():
        categorias = Categoria.objects.all()
        serializer = CategoriasSerializerReg(categorias, many=True)
        return Response(serializer.data, status=HTTP_200_OK)

    return TryCatch(action_to_execute)


pk_paramView = OpenApiParameter(
    'id_categoria',
    OpenApiTypes.INT,
    OpenApiParameter.QUERY,
    description="ID de la categoría",
)


@extend_schema(
    description="Obtener una categoría por su ID",
    parameters=[pk_paramView],
    responses={200: CategoriasSerializer(many=True), 404: OpenApiTypes.OBJECT})

@api_view(['GET'])
def Categoria_View(request):
    id = request.GET.get('id_categoria')
    if not id:
        return Result.Error("Complete la casilla del ID de la categoria")

    categoria = Categoria.objects.filter(id_categoria=id)
    serialData = CategoriasSerializer(categoria, many=True)

    return Result.Exitosa("", serialData.data, HTTP_200_OK)


@extend_schema(
    description='Añade una nueva categoria.',
    request=CategoriasSerializerReg,
    responses={201: CategoriasSerializerReg, 400: OpenApiTypes.OBJECT})

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


@extend_schema(
    description="Actualiza una categoria.",
    request=CategoriasSerializerUpdate,
    responses={200: CategoriasSerializerUpdate, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT})

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


@extend_schema(
    description="Eliminar un Categoria",
    parameters=[pk_paramView],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT})

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

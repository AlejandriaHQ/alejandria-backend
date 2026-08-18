from .serializersLibros import LibroSerializer, LibroSerializerReg, LibroSerializerUpdate, LibroSerializerDelete
from rest_framework.decorators import api_view
from biblioteca.models import Libro
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from django.db.models import Q, ProtectedError
from django.core.paginator import Paginator
from ..services.response import Result, TryCatch

#Libros Views


@extend_schema(
    description="Obtener la lista de libros",
    responses={200: OpenApiTypes.OBJECT})

@api_view(['GET'])
def libros_list(request):
    def action_to_execute():
        libros = Libro.objects.all()
        serializer = LibroSerializerReg(libros, many=True)
        return Result.Exitosa("Lista de libros obtenida correctamente", serializer.data)

    return TryCatch(action_to_execute)


pk_paramView = OpenApiParameter(
    'id_libro', OpenApiTypes.INT, OpenApiParameter.QUERY,
    description="ID del libro")


@extend_schema(
    description="Obtener un libro por su ID",
    parameters=[pk_paramView],
    responses={200: LibroSerializer(many=True), 404: OpenApiTypes.OBJECT})

@api_view(['GET'])
def Libro_View(request):
    id = request.GET.get('id_libro')
    if not id:
        return Result.Error("Complete la casilla del ID del libro")

    libro = Libro.objects.filter(id_libro=id)
    serialData = LibroSerializer(libro, many=True)

    return Result.Exitosa("", serialData.data, HTTP_200_OK)


@extend_schema(
    description='Añade un nuevo libro.',
    request=LibroSerializerReg,
    responses={201: LibroSerializerReg, 400: OpenApiTypes.OBJECT})

@api_view(['POST'])
def Libro_Add(request):
    titulo = request.data.get('titulo')
    autor = request.data.get('autor')
    id_categoria = request.data.get('id_categoria')

    errores = []
    if not titulo:
        errores.append("Complete la casilla titulo")
    if not autor:
        errores.append("Complete la casilla autor")
    if not id_categoria:
        errores.append("Complete la casilla id_categoria")

    if errores:
        return Result.Error(errores)

    serialData = LibroSerializerReg(data=request.data)

    if serialData.is_valid():
        serialData.save()
    else:
        return Result.Error("Complete los campos vacios")

    return Result.Exitosa("Se registro correctamente", serialData.data, HTTP_201_CREATED)


@extend_schema(
    description="Actualiza un libro.",
    request=LibroSerializerUpdate,
    responses={200: LibroSerializerUpdate, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT})

@api_view(['PUT'])
def Libro_Update(request):
    pk = request.data.get('id_libro')

    titulo = request.data.get('titulo')
    autor = request.data.get('autor')
    id_categoria = request.data.get('id_categoria')

    errores = []
    if not pk:
        errores.append("Complete la casilla del ID del libro")
    if not titulo:
        errores.append("Complete la casilla titulo")

    if not autor:
        errores.append("Complete la casilla autor")

    if not id_categoria:
        errores.append("Complete la casilla id_categoria")

    if errores:
        return Result.Error(errores)

    try:
        libro = Libro.objects.get(id_libro=pk)
    except Libro.DoesNotExist:
        return Result.Error("El libro no existe")

    serialData = LibroSerializerUpdate(instance=libro, data=request.data)

    if serialData.is_valid():
        serialData.save()
    else:
        return Result.Error("Complete los campos vacios")

    return Result.Exitosa("Se actualizo correctamente", serialData.data, HTTP_200_OK)


pk_paramView = OpenApiParameter(
    'id_libro',
    OpenApiTypes.INT,
    OpenApiParameter.QUERY,
    description="ID del libro",
)


@extend_schema(
    description="Eliminar un libro",
    parameters=[pk_paramView],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT})

@api_view(['DELETE'])
def Libro_Delete(request):

    pk = request.GET.get('id_libro')
    if not pk:
        return Result.Error("Complete la casilla del ID del libro")

    try:
        libro = Libro.objects.get(id_libro=pk)
    except Libro.DoesNotExist:
        return Result.Error("El libro no existe")

    try:
        libro.delete()
    except ProtectedError:
        return Result.Error("No se puede eliminar: el libro tiene prestamos asociados")

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
def Libro_Paginators(request):
    page = request.GET.get('page')
    pagesize = 10
    filter = request.GET.get('filter')

    if filter:
        query = Q(titulo__icontains=filter) | \
                Q(autor__icontains=filter) | \
                Q(isbn__icontains=filter)

        cont = Libro.objects.filter(query).order_by('id_libro')

    else:
        cont = Libro.objects.all().order_by('id_libro')

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

    serialdata = LibroSerializer(page_obj, many=True)

    return Result.ResponsePaginator('', serialdata.data, total_pages, page, button_previous, button_next)

from .serializers import UsuarioSerializer, UsuarioSerializerReg, UsuarioSerializerUpdate, UsuarioSerializerDelete
from rest_framework.decorators import api_view
from biblioteca.models import Usuario
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from django.db.models import Q, ProtectedError
from django.db import IntegrityError
from django.core.paginator import Paginator
from ..services.response import Result, TryCatch

#Usuarios Views


@extend_schema(
    description="Obtener la lista de usuarios",
    responses={200: OpenApiTypes.OBJECT})

@api_view(['GET'])
def usuarios_list(request):
    def action_to_execute():
        usuarios = Usuario.objects.all()
        serializer = UsuarioSerializerReg(usuarios, many=True)
        return Result.Exitosa("Lista de usuarios obtenida correctamente", serializer.data)

    return TryCatch(action_to_execute)


pk_paramView = OpenApiParameter(
    'id_usuario', OpenApiTypes.INT, OpenApiParameter.QUERY,
    description="ID del usuario")


@extend_schema(
    description="Obtener un usuario por su ID",
    parameters=[pk_paramView],
    responses={200: UsuarioSerializer(many=True), 404: OpenApiTypes.OBJECT})

@api_view(['GET'])
def Usuario_View(request):
    id = request.GET.get('id_usuario')
    if not id:
        return Result.Error("Complete la casilla del ID del usuario")

    usuario = Usuario.objects.filter(id_usuario=id)
    if not usuario.exists():
        return Result.Error("Registro no encontrado", 404)

    serialData = UsuarioSerializer(usuario, many=True)

    return Result.Exitosa("", serialData.data, HTTP_200_OK)


@extend_schema(
    description='Añade un nuevo usuario.',
    request=UsuarioSerializerReg,
    responses={201: UsuarioSerializerReg, 400: OpenApiTypes.OBJECT})

@api_view(['POST'])
def Usuario_Add(request):
    nombre = request.data.get('nombre')
    apellido = request.data.get('apellido')
    correo = request.data.get('correo')
    contrasena = request.data.get('contrasena')

    errores = []
    if not nombre:
        errores.append("Complete la casilla nombre")
    if not apellido:
        errores.append("Complete la casilla apellido")
    if not correo:
        errores.append("Complete la casilla correo")
    if not contrasena:
        errores.append("Complete la casilla contrasena")

    if errores:
        return Result.Error(errores)

    serialData = UsuarioSerializerReg(data=request.data)

    if serialData.is_valid():
        try:
            serialData.save()
        except IntegrityError:
            return Result.Error("Ya existe un registro con ese valor único", 400)
    else:
        # Se devuelven los errores del serializer (p. ej. "Ya existe un usuario
        # con ese correo") en lugar del mensaje genérico y engañoso.
        return Result.Error(serialData.errors)

    return Result.Exitosa("Se registro correctamente", serialData.data, HTTP_201_CREATED)


@extend_schema(
    description="Actualiza un usuario.",
    request=UsuarioSerializerUpdate,
    responses={200: UsuarioSerializerUpdate, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT})

@api_view(['PUT'])
def Usuario_Update(request):
    pk = request.data.get('id_usuario')

    nombre = request.data.get('nombre')
    apellido = request.data.get('apellido')
    correo = request.data.get('correo')

    errores = []
    if not pk:
        errores.append("Complete la casilla del ID del usuario")
    if not nombre:
        errores.append("Complete la casilla nombre")

    if not apellido:
        errores.append("Complete la casilla apellido")

    if not correo:
        errores.append("Complete la casilla correo")

    if errores:
        return Result.Error(errores)

    try:
        usuario = Usuario.objects.get(id_usuario=pk)
    except Usuario.DoesNotExist:
        return Result.Error("Registro no encontrado", 404)

    serialData = UsuarioSerializerUpdate(instance=usuario, data=request.data)

    if serialData.is_valid():
        try:
            serialData.save()
        except IntegrityError:
            return Result.Error("Ya existe un registro con ese valor único", 400)
    else:
        # Se devuelven los errores del serializer (p. ej. "Ya existe un usuario
        # con ese correo") en lugar del mensaje genérico y engañoso.
        return Result.Error(serialData.errors)

    return Result.Exitosa("Se actualizo correctamente", serialData.data, HTTP_200_OK)


pk_paramView = OpenApiParameter(
    'id_usuario',
    OpenApiTypes.INT,
    OpenApiParameter.QUERY,
    description="ID del usuario",
)


@extend_schema(
    description="Eliminar un usuario",
    parameters=[pk_paramView],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT})

@api_view(['DELETE'])
def Usuario_Delete(request):

    pk = request.GET.get('id_usuario')
    if not pk:
        return Result.Error("Complete la casilla del ID del usuario")

    try:
        usuario = Usuario.objects.get(id_usuario=pk)
    except Usuario.DoesNotExist:
        return Result.Error("Registro no encontrado", 404)

    try:
        usuario.delete()
    except ProtectedError:
        return Result.Error("No se puede eliminar: el usuario tiene prestamos asociados")

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
def Usuario_Paginators(request):
    page = request.GET.get('page')
    pagesize = 10
    filter = request.GET.get('filter')

    if filter:
        query = Q(nombre__icontains=filter) | \
                Q(apellido__icontains=filter) | \
                Q(correo__icontains=filter)

        cont = Usuario.objects.filter(query).order_by('id_usuario')

    else:
        cont = Usuario.objects.all().order_by('id_usuario')

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

    serialdata = UsuarioSerializer(page_obj, many=True)

    return Result.ResponsePaginator('', serialdata.data, total_pages, page, button_previous, button_next)

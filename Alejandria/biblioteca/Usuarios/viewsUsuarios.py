from .serializersUsuarios import UsuarioSerializer, UsuarioSerializerReg, UsuarioSerializerUpdate, UsuarioSerializerDelete
from rest_framework.decorators import api_view
from biblioteca.models import Usuario
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db.models import Q, ProtectedError
from django.core.paginator import Paginator
from ..services.response import Result, TryCatch

#Usuarios Views


@api_view(['GET'])
def usuarios_list(request):
    def action_to_execute():
        usuarios = Usuario.objects.all()
        serializer = UsuarioSerializerReg(usuarios, many=True)
        return Response(serializer.data, status=HTTP_200_OK)

    return TryCatch(action_to_execute)


pk_paramView = openapi.Parameter(
    'id_usuario', openapi.IN_QUERY,
    description="ID del usuario",
    type=openapi.TYPE_INTEGER)


@swagger_auto_schema(
    method='get', operation_description="Obtener un usuario por su ID", manual_parameters=[pk_paramView], responses={200: 'Exitoso', 400: 'Error'})

@api_view(['GET'])
def Usuario_View(request):
    id = request.GET.get('id_usuario')
    if not id:
        return Result.Error("Complete la casilla del ID del usuario")

    usuario = Usuario.objects.filter(id_usuario=id)
    serialData = UsuarioSerializer(usuario, many=True)

    return Result.Exitosa("", serialData.data, HTTP_200_OK)


@swagger_auto_schema(
    method='post',
    operation_description='Añade un nuevo usuario.',
    request_body=UsuarioSerializerReg,
    responses={200: 'Exitoso', 400: 'Error'})

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
        serialData.save()
    else:
        return Result.Error("Complete los campos vacios")

    return Result.Exitosa("Se registro correctamente", serialData.data, HTTP_201_CREATED)


@swagger_auto_schema(
    method='put',
    operation_description="Actualiza un usuario.",
    request_body=UsuarioSerializerUpdate,
    responses={200: 'Exitoso', 400: 'Error'})

@api_view(['PUT'])
def Usuario_Update(request):
    pk = request.data.get('id_usuario')

    nombre = request.data.get('nombre')
    apellido = request.data.get('apellido')
    correo = request.data.get('correo')
    contrasena = request.data.get('contrasena')

    errores = []
    if not pk:
        errores.append("Complete la casilla del ID del usuario")
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

    try:
        usuario = Usuario.objects.get(id_usuario=pk)
    except Usuario.DoesNotExist:
        return Result.Error("El usuario no existe")

    serialData = UsuarioSerializerUpdate(instance=usuario, data=request.data)

    if serialData.is_valid():
        serialData.save()
    else:
        return Result.Error("Complete los campos vacios")

    return Result.Exitosa("Se actualizo correctamente", serialData.data, HTTP_200_OK)


pk_paramView = openapi.Parameter(
    'id_usuario',
    openapi.IN_QUERY,
    description="ID del usuario",
    type=openapi.TYPE_INTEGER,
)


@swagger_auto_schema(
    method='delete',
    operation_description="Eliminar un usuario",
    manual_parameters=[pk_paramView],
    responses={200: 'Exitoso', 400: 'Error'})

@api_view(['DELETE'])
def Usuario_Delete(request):

    pk = request.GET.get('id_usuario')
    if not pk:
        return Result.Error("Complete la casilla del ID del usuario")

    try:
        usuario = Usuario.objects.get(id_usuario=pk)
    except Usuario.DoesNotExist:
        return Result.Error("El usuario no existe")

    try:
        usuario.delete()
    except ProtectedError:
        return Result.Error("No se puede eliminar: el usuario tiene prestamos asociados")

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

    if page == total_pages:
        button_previous = True
        button_next = False
    elif page <= 1:
        button_previous = False
        button_next = True
    else:
        button_previous = True
        button_next = True

    serialdata = UsuarioSerializer(page_obj, many=True)

    return Result.ResponsePaginator('', serialdata.data, total_pages, page, button_previous, button_next)

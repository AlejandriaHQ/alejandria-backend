from .serializersPrestamos import PrestamoSerializer, PrestamoSerializerReg, PrestamoSerializerUpdate, PrestamoSerializerDelete
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db.models import Q, ProtectedError
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta
from ..services.response import Result, TryCatch
from ..services.permissions import IsAdminUser, IsAuthenticated
from ..models import Prestamo
from ..models import Libro
from ..models import Usuario

@api_view(['GET'])
def prestamos_list(request):
    if not IsAdminUser().has_permission(request, None):
        return Result.Error("Solo administradores", status=HTTP_403_FORBIDDEN)
    
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
    method='get', operation_description="Obtener un prestamo por su ID", 
    manual_parameters=[pk_paramView], responses={200: 'Exitoso', 400: 'Error'})

@api_view(['GET'])
def Prestamo_View(request):
    if not IsAuthenticated().has_permission(request, None):
        return Result.Error("Debes iniciar sesión", status=HTTP_401_UNAUTHORIZED)
    
    id = request.GET.get('id_prestamo')
    if not id:
        return Result.Error("Complete la casilla del ID del prestamo")

    try:
        prestamo = Prestamo.objects.get(id_prestamo=id)
    except Prestamo.DoesNotExist:
        return Result.Error("El préstamo no existe")
    
    # Verificar que sea el dueño o admin
    if not request.user.is_staff and prestamo.id_usuario.id_usuario != request.user.id:
        return Result.Error("No tienes permiso para ver este préstamo", status=HTTP_403_FORBIDDEN)
    
    serialData = PrestamoSerializer(prestamo)
    return Result.Exitosa("", serialData.data, HTTP_200_OK)

@swagger_auto_schema(
    method='post',
    operation_description='Crear un nuevo préstamo.',
    request_body=PrestamoSerializerReg,
    responses={200: 'Exitoso', 400: 'Error'})

@api_view(['POST'])
def Prestamo_Add(request):
    if not IsAuthenticated().has_permission(request, None):
        return Result.Error("Debes iniciar sesión", status=HTTP_401_UNAUTHORIZED)
    
    id_libro = request.data.get('id_libro')
    if not id_libro:
        return Result.Error("Complete la casilla id_libro")
    
    #Validar que el libro exista
    try:
        libro = Libro.objects.get(id_libro=id_libro)
    except Libro.DoesNotExist:
        return Result.Error("El libro no existe")
    
    #Obtener el usuario personalizado usando el campo id_usuario
    try:
        usuario = Usuario.objects.get(id_usuario=request.user.id)
    except Usuario.DoesNotExist:
        return Result.Error("Usuario no encontrado")
    
    #maximo 3 libros por usuario
    prestamos_activos = Prestamo.objects.filter(
        id_usuario=usuario,
        devuelto=False
    ).count()
    
    if prestamos_activos >= 3:
        return Result.Error(f"Máximo 3 libros por usuario. Tienes {prestamos_activos} activos.")
    
    #Verificar disponibilidad del libro
    prestamo_activo = Prestamo.objects.filter(
        id_libro=libro,
        devuelto=False
    ).exists()
    
    if prestamo_activo:
        return Result.Error(f"El libro '{libro.titulo}' no está disponible")
    
    #Crear préstamo
    prestamo = Prestamo.objects.create(
        id_libro=libro,
        id_usuario=usuario,
        fecha_prestamo=timezone.now().date(),
        fecha_devolucion=timezone.now().date() + timedelta(days=7),
        estado=Prestamo.ESTADO_PRESTADO,
        devuelto=False
    )
    
    serialData = PrestamoSerializer(prestamo)
    return Result.Exitosa("Préstamo creado exitosamente", serialData.data, HTTP_201_CREATED)

@swagger_auto_schema(
    method='patch',
    operation_description="Devolver un libro (marcar como devuelto)",
    responses={200: 'Exitoso', 400: 'Error'})

@api_view(['PATCH'])
def Prestamo_Devolver(request, id_prestamo):
    if not IsAuthenticated().has_permission(request, None):
        return Result.Error("Debes iniciar sesión", status=HTTP_401_UNAUTHORIZED)
    
    try:
        prestamo = Prestamo.objects.get(id_prestamo=id_prestamo)
    except Prestamo.DoesNotExist:
        return Result.Error("El préstamo no existe")
    
    #Verificar que sea el dueño o admin
    if not request.user.is_staff and prestamo.id_usuario.id_usuario != request.user.id:
        return Result.Error("No tienes permiso para devolver este préstamo", status=HTTP_403_FORBIDDEN)
    
    if prestamo.devuelto:
        return Result.Error("Este préstamo ya fue devuelto")
    
    prestamo.devuelto = True
    prestamo.estado = Prestamo.ESTADO_DEVUELTO
    prestamo.fecha_devolucion_real = timezone.now()
    prestamo.save()
    
    return Result.Exitosa("Libro devuelto exitosamente", {}, HTTP_200_OK)

@api_view(['GET'])
def Prestamo_Historial(request):
    if not IsAuthenticated().has_permission(request, None):
        return Result.Error("Debes iniciar sesión", status=HTTP_401_UNAUTHORIZED)
    
    try:
        usuario = Usuario.objects.get(id_usuario=request.user.id)
    except Usuario.DoesNotExist:
        return Result.Error("Usuario no encontrado")
    
    prestamos = Prestamo.objects.filter(id_usuario=usuario)
    serialData = PrestamoSerializer(prestamos, many=True)
    return Result.Exitosa("", serialData.data, HTTP_200_OK)

@api_view(['GET'])
def Prestamo_Activos(request):
    if not IsAuthenticated().has_permission(request, None):
        return Result.Error("Debes iniciar sesión", status=HTTP_401_UNAUTHORIZED)
    
    try:
        usuario = Usuario.objects.get(id_usuario=request.user.id)
    except Usuario.DoesNotExist:
        return Result.Error("Usuario no encontrado")
    
    prestamos = Prestamo.objects.filter(id_usuario=usuario, devuelto=False)
    serialData = PrestamoSerializer(prestamos, many=True)
    return Result.Exitosa("", serialData.data, HTTP_200_OK)

@api_view(['GET'])
def Prestamo_Vencidos(request):
    if not IsAdminUser().has_permission(request, None):
        return Result.Error("Solo administradores", status=HTTP_403_FORBIDDEN)
    
    vencidos = Prestamo.objects.filter(
        devuelto=False,
        fecha_devolucion__lt=timezone.now().date()
    )
    serialData = PrestamoSerializer(vencidos, many=True)
    return Result.Exitosa("", serialData.data, HTTP_200_OK)

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
    if not IsAdminUser().has_permission(request, None):
        return Result.Error("Solo administradores", status=HTTP_403_FORBIDDEN)
    
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
    if not IsAuthenticated().has_permission(request, None):
        return Result.Error("Debes iniciar sesión", status=HTTP_401_UNAUTHORIZED)
    
    page = request.GET.get('page')
    pagesize = 10
    filter = request.GET.get('filter')
    
    #Obtener el usuario personalizado
    try:
        usuario = Usuario.objects.get(id_usuario=request.user.id)
    except Usuario.DoesNotExist:
        return Result.Error("Usuario no encontrado")
    
    #Si es admin ve todos, si no solo los suyos
    if request.user.is_staff:
        prestamos = Prestamo.objects.all()
    else:
        prestamos = Prestamo.objects.filter(id_usuario=usuario)

    if filter:
        query = Q(estado__icontains=filter)
        cont = prestamos.filter(query).order_by('id_prestamo')
    else:
        cont = prestamos.all().order_by('id_prestamo')

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
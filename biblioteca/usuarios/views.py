from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q, ProtectedError
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_403_FORBIDDEN,
)
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter

from ..models import Usuario
from ..services.response import Result
from .serializers import (
    UsuarioSerializer,
    UsuarioSerializerReg,
    UsuarioSerializerUpdate,
    UsuarioSerializerDelete,
)


# PROTECCIÓN DE ESCRITURA (roles) — cómo se implementó:
# Solo un usuario con role='admin' o is_staff puede crear, actualizar o
# eliminar usuarios; esto incluye la asignación de role='admin' en el payload
# (un usuario común jamás llega al serializer, ni siquiera con role='admin').
# La lectura (list/retrieve/paginar) queda abierta a cualquier usuario
# autenticado (IsAuthenticated global en settings).
# Se implementa con LÓGICA EN LA VISTA (y no con permission_classes de DRF)
# para mantener el envelope JSON {success, Mensaje, datos} consistente:
# PermissionDenied lanzaría un 403 con el body por defecto de DRF, fuera del
# contrato que consume el frontend. La comprobación es role=='admin' OR
# is_staff: así los superusuarios de Django (is_staff/is_superuser) también
# administran el panel sin depender de su campo role.
def _permiso_escritura_usuarios(request):
    return request.user.role == 'admin' or request.user.is_staff


def _obtener_o_none(queryset, pk):
    """Devuelve el registro por pk, o None si no existe o el pk no es numérico.

    Un pk no numérico (p.ej. /usuarios/abc/) lanza ValueError al filtrar
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


@extend_schema(tags=['usuarios'])
class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    http_method_names = ['get', 'post', 'put', 'delete']

    @extend_schema(
        description="Obtener la lista de usuarios",
        responses={200: OpenApiTypes.OBJECT})
    def list(self, request):
        usuarios = Usuario.objects.all()
        serializer = UsuarioSerializer(usuarios, many=True)
        return Result.Exitosa("Lista de usuarios obtenida correctamente", serializer.data)

    @extend_schema(
        description='Añade un nuevo usuario.',
        request=UsuarioSerializerReg,
        responses={201: UsuarioSerializerReg, 400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT})
    def create(self, request):
        if not _permiso_escritura_usuarios(request):
            return Result.Error("No tiene permisos para realizar esta acción", HTTP_403_FORBIDDEN)

        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name')
        email = request.data.get('email')
        password = request.data.get('password')
        role = request.data.get('role')
        cedula = request.data.get('cedula')

        errores = []
        if not first_name:
            errores.append("Complete la casilla first_name")
        if not last_name:
            errores.append("Complete la casilla last_name")
        if not email:
            errores.append("Complete la casilla email")
        if not password:
            errores.append("Complete la casilla password")
        if not role:
            errores.append("Complete la casilla role")
        if not cedula:
            errores.append("Complete la casilla cedula")

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
            # con ese email") en lugar del mensaje genérico y engañoso.
            return Result.Error(serialData.errors)

        return Result.Exitosa("Se registro correctamente", serialData.data, HTTP_201_CREATED)

    @extend_schema(
        description="Obtener un usuario por su ID",
        responses={200: UsuarioSerializer, 404: OpenApiTypes.OBJECT})
    def retrieve(self, request, pk=None):
        usuario = _obtener_o_none(Usuario.objects, pk)
        if not usuario:
            return Result.Error("Registro no encontrado", 404)

        serialData = UsuarioSerializer(usuario)
        return Result.Exitosa("", serialData.data, HTTP_200_OK)

    @extend_schema(
        description="Actualiza un usuario.",
        request=UsuarioSerializerUpdate,
        responses={200: UsuarioSerializerUpdate, 400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT})
    def update(self, request, pk=None):
        if not _permiso_escritura_usuarios(request):
            return Result.Error("No tiene permisos para realizar esta acción", HTTP_403_FORBIDDEN)

        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name')
        email = request.data.get('email')

        errores = []
        if not first_name:
            errores.append("Complete la casilla first_name")

        if not last_name:
            errores.append("Complete la casilla last_name")

        if not email:
            errores.append("Complete la casilla email")

        if errores:
            return Result.Error(errores)

        usuario = _obtener_o_none(Usuario.objects, pk)
        if not usuario:
            return Result.Error("Registro no encontrado", 404)

        serialData = UsuarioSerializerUpdate(instance=usuario, data=request.data)

        if serialData.is_valid():
            try:
                serialData.save()
            except IntegrityError:
                return Result.Error("Ya existe un registro con ese valor único", 400)
        else:
            # Se devuelven los errores del serializer (p. ej. "Ya existe un usuario
            # con ese email") en lugar del mensaje genérico y engañoso.
            return Result.Error(serialData.errors)

        return Result.Exitosa("Se actualizo correctamente", serialData.data, HTTP_200_OK)

    @extend_schema(
        description="Eliminar un usuario",
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT})
    def destroy(self, request, pk=None):
        if not _permiso_escritura_usuarios(request):
            return Result.Error("No tiene permisos para realizar esta acción", HTTP_403_FORBIDDEN)

        usuario = _obtener_o_none(Usuario.objects, pk)
        if not usuario:
            return Result.Error("Registro no encontrado", 404)

        try:
            usuario.delete()
        except ProtectedError:
            return Result.Error("No se puede eliminar: el usuario tiene prestamos asociados")

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

        if filter:
            query = Q(first_name__icontains=filter) | \
                    Q(last_name__icontains=filter) | \
                    Q(email__icontains=filter)

            cont = Usuario.objects.filter(query).order_by('id')

        else:
            cont = Usuario.objects.all().order_by('id')

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

        serialdata = UsuarioSerializer(page_obj, many=True)

        return Result.ResponsePaginator('', serialdata.data, total_pages, page, button_previous, button_next)

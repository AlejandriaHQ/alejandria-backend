from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q, ProtectedError
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED
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
        serializer = UsuarioSerializerReg(usuarios, many=True)
        return Result.Exitosa("Lista de usuarios obtenida correctamente", serializer.data)

    @extend_schema(
        description='Añade un nuevo usuario.',
        request=UsuarioSerializerReg,
        responses={201: UsuarioSerializerReg, 400: OpenApiTypes.OBJECT})
    def create(self, request):
        nombre = request.data.get('nombre')
        apellido = request.data.get('apellido')
        correo = request.data.get('correo')
        password = request.data.get('password')

        errores = []
        if not nombre:
            errores.append("Complete la casilla nombre")
        if not apellido:
            errores.append("Complete la casilla apellido")
        if not correo:
            errores.append("Complete la casilla correo")
        if not password:
            errores.append("Complete la casilla password")

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
        responses={200: UsuarioSerializerUpdate, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT})
    def update(self, request, pk=None):
        nombre = request.data.get('nombre')
        apellido = request.data.get('apellido')
        correo = request.data.get('correo')

        errores = []
        if not nombre:
            errores.append("Complete la casilla nombre")

        if not apellido:
            errores.append("Complete la casilla apellido")

        if not correo:
            errores.append("Complete la casilla correo")

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
            # con ese correo") en lugar del mensaje genérico y engañoso.
            return Result.Error(serialData.errors)

        return Result.Exitosa("Se actualizo correctamente", serialData.data, HTTP_200_OK)

    @extend_schema(
        description="Eliminar un usuario",
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT})
    def destroy(self, request, pk=None):
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

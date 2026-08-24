from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q, ProtectedError
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_403_FORBIDDEN
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter

from ..models import Categoria, Libro
from ..services.response import Result
from .serializers import (
    CategoriasSerializer,
    CategoriasSerializerReg,
    CategoriasSerializerUpdate,
    CategoriasSerializerDelete,
)


def _obtener_o_none(queryset, pk):
    """Devuelve el registro por pk, o None si no existe o el pk no es numérico.

    Un pk no numérico (p.ej. /categorias/abc/) lanza ValueError al filtrar
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


def _permiso_escritura_catalogo(request):
    return request.user.role == 'admin' or request.user.is_staff


@extend_schema(tags=['categorias'])
class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriasSerializer
    http_method_names = ['get', 'post', 'put', 'delete']

    @extend_schema(
        description="Obtener la lista de categorías",
        responses={200: OpenApiTypes.OBJECT})
    def list(self, request):
        categorias = Categoria.objects.filter(activo=True)
        serializer = CategoriasSerializerReg(categorias, many=True)
        return Result.Exitosa("Lista de categorías obtenida correctamente", serializer.data)

    @extend_schema(
        description='Añade una nueva categoria.',
        request=CategoriasSerializerReg,
        responses={201: CategoriasSerializerReg, 400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT})
    def create(self, request):
        # RN-05 / RFC-25: solo un administrador puede registrar categorías.
        if not _permiso_escritura_catalogo(request):
            return Result.Error("No tiene permisos para realizar esta acción", HTTP_403_FORBIDDEN)

        errores = []

        nombre = request.data.get('nombre')
        if not nombre:
            errores.append("Complete la casilla nombre")

        if errores:
            return Result.Error(errores)

        serialData = CategoriasSerializerReg(data=request.data)

        if not serialData.is_valid():
            # F13 pentest: se devuelven los errores reales del serializer
            # (p. ej. nombre con más de 100 caracteres) en lugar del genérico
            # "Complete los campos vacios"; mismo patrón que libros, usuarios
            # y préstamos.
            return Result.Error(serialData.errors)

        try:
            serialData.save()
        except IntegrityError:
            return Result.Error("Ya existe un registro con ese valor único", 400)

        return Result.Exitosa("Se registro correctamente", serialData.data, HTTP_201_CREATED)

    @extend_schema(
        description="Obtener una categoría por su ID",
        responses={200: CategoriasSerializer, 404: OpenApiTypes.OBJECT})
    def retrieve(self, request, pk=None):
        categoria = _obtener_o_none(Categoria.objects, pk)
        if not categoria:
            return Result.Error("Registro no encontrado", 404)

        serialData = CategoriasSerializer(categoria)
        return Result.Exitosa("", serialData.data, HTTP_200_OK)

    @extend_schema(
        description="Actualiza una categoria.",
        request=CategoriasSerializerUpdate,
        responses={200: CategoriasSerializerUpdate, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT})
    def update(self, request, pk=None):
        # RN-05 / RFC-25: solo un administrador puede actualizar una categoría.
        if not _permiso_escritura_catalogo(request):
            return Result.Error("No tiene permisos para realizar esta acción", HTTP_403_FORBIDDEN)

        errores = []

        nombre = request.data.get('nombre')

        if not nombre:
            errores.append("Complete la casilla nombre")

        if errores:
            return Result.Error(errores)

        categoria = _obtener_o_none(Categoria.objects, pk)
        if not categoria:
            return Result.Error("Registro no encontrado", 404)

        serialData = CategoriasSerializerUpdate(instance=categoria, data=request.data)

        if not serialData.is_valid():
            # F13 pentest: se devuelven los errores reales del serializer en
            # lugar del genérico "Complete los campos vacios" (ver create).
            return Result.Error(serialData.errors)

        try:
            serialData.save()
        except IntegrityError:
            return Result.Error("Ya existe un registro con ese valor único", 400)

        return Result.Exitosa("Se actualizo correctamente", serialData.data, HTTP_200_OK)

    @extend_schema(
        description="Eliminar un Categoria",
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT})
    def destroy(self, request, pk=None):
        # RN-05 / RFC-25: solo un administrador puede eliminar categorías.
        if not _permiso_escritura_catalogo(request):
            return Result.Error("No tiene permisos para realizar esta acción", HTTP_403_FORBIDDEN)

        categoria = _obtener_o_none(Categoria.objects, pk)
        if not categoria:
            return Result.Error("Registro no encontrado", 404)

        # Eliminación lógica (RN-07 / RF-10): si la categoría tiene libros
        # asociados no se borra físicamente (PROTECT); se desactiva para no
        # romper la FK de los libros que la referencian.
        tiene_libros = Libro.objects.filter(id_categoria=categoria).exists()
        if tiene_libros:
            categoria.activo = False
            categoria.save(update_fields=['activo'])
            return Result.Exitosa(
                "La categoría tiene libros asociados, por lo que se desactivó en lugar de eliminarse",
                {},
                HTTP_200_OK,
            )

        # Sin libros: se puede eliminar físicamente.
        try:
            categoria.delete()
        except ProtectedError:
            return Result.Error("No se puede eliminar: la categoria tiene libros asociados")

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
                    Q(descripcion__icontains=filter)

            cont = Categoria.objects.filter(activo=True).filter(query).order_by('id_categoria')
        else:
            cont = Categoria.objects.filter(activo=True).order_by('id_categoria')

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

        serialdata = CategoriasSerializer(page_obj, many=True)

        return Result.ResponsePaginator('', serialdata.data, total_pages, page, button_previous, button_next)

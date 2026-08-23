from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q, ProtectedError
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter

from ..models import Libro, Prestamo
from ..services.response import Result
from .serializers import (
    LibroSerializer,
    LibroSerializerReg,
    LibroSerializerUpdate,
    LibroSerializerDelete,
)


def _obtener_o_none(queryset, pk):
    """Devuelve el registro por pk, o None si no existe o el pk no es numérico.

    Un pk no numérico (p.ej. /libros/abc/) lanza ValueError al filtrar
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

categoria_paramView = OpenApiParameter(
    'categoria',
    OpenApiTypes.INT,
    OpenApiParameter.QUERY,
    description="ID de categoría para filtrar libros",
)


@extend_schema(tags=['libros'])
class LibroViewSet(viewsets.ModelViewSet):
    queryset = Libro.objects.all()
    serializer_class = LibroSerializer
    http_method_names = ['get', 'post', 'put', 'delete']

    @extend_schema(
        description="Obtener la lista de libros",
        responses={200: OpenApiTypes.OBJECT})
    def list(self, request):
        libros = Libro.objects.filter(activo=True)
        serializer = LibroSerializerReg(libros, many=True)
        return Result.Exitosa("Lista de libros obtenida correctamente", serializer.data)

    @extend_schema(
        description='Añade un nuevo libro.',
        request=LibroSerializerReg,
        responses={201: LibroSerializerReg, 400: OpenApiTypes.OBJECT})
    def create(self, request):
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
            try:
                serialData.save()
            except IntegrityError:
                return Result.Error("Ya existe un registro con ese valor único", 400)
        else:
            # Se devuelven los errores del serializer (p. ej. "Ya existe un libro
            # con ese ISBN") en lugar del mensaje genérico y engañoso.
            return Result.Error(serialData.errors)

        return Result.Exitosa("Se registro correctamente", serialData.data, HTTP_201_CREATED)

    @extend_schema(
        description="Obtener un libro por su ID",
        responses={200: LibroSerializer, 404: OpenApiTypes.OBJECT})
    def retrieve(self, request, pk=None):
        libro = _obtener_o_none(Libro.objects, pk)
        if not libro:
            return Result.Error("Registro no encontrado", 404)

        serialData = LibroSerializer(libro)
        return Result.Exitosa("", serialData.data, HTTP_200_OK)

    @extend_schema(
        description="Actualiza un libro.",
        request=LibroSerializerUpdate,
        responses={200: LibroSerializerUpdate, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT})
    def update(self, request, pk=None):
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

        libro = _obtener_o_none(Libro.objects, pk)
        if not libro:
            return Result.Error("Registro no encontrado", 404)

        serialData = LibroSerializerUpdate(instance=libro, data=request.data)

        if serialData.is_valid():
            try:
                serialData.save()
            except IntegrityError:
                return Result.Error("Ya existe un registro con ese valor único", 400)
        else:
            # Se devuelven los errores del serializer (p. ej. "Ya existe un libro
            # con ese ISBN") en lugar del mensaje genérico y engañoso.
            return Result.Error(serialData.errors)

        return Result.Exitosa("Se actualizo correctamente", serialData.data, HTTP_200_OK)

    @extend_schema(
        description="Eliminar un libro",
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT})
    def destroy(self, request, pk=None):
        libro = _obtener_o_none(Libro.objects, pk)
        if not libro:
            return Result.Error("Registro no encontrado", 404)

        # Eliminación lógica (RN-06 / RF-07): si el libro tiene préstamos
        # asociados (en curso o historial) no se borra físicamente: el FK de
        # Prestamo usa PROTECT y además se pierde el historial. Se desactiva
        # para que deje de aparecer en el catálogo público.
        tiene_prestamos = Prestamo.objects.filter(id_libro=libro).exists()
        if tiene_prestamos:
            libro.activo = False
            libro.save(update_fields=['activo'])
            return Result.Exitosa(
                "El libro tiene préstamos asociados, por lo que se desactivó en lugar de eliminarse",
                {},
                HTTP_200_OK,
            )

        # Sin préstamos: se puede eliminar físicamente.
        try:
            libro.delete()
        except ProtectedError:
            return Result.Error("No se puede eliminar: el libro tiene prestamos asociados")

        return Result.Exitosa("Se elimino correctamente", {}, HTTP_200_OK)

    @extend_schema(
        description="Buscar",
        parameters=[page_paramView, filter_paramView, categoria_paramView],
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT})
    @action(detail=False, methods=['get'], url_path='paginar')
    def paginar(self, request):
        """Paginación con búsqueda combinable (RF-08).

        Solo se listan libros activos (``activo=True``): los desactivados
        por eliminación lógica no aparecen en el catálogo público (RN-06).

        Filtros de la lista (se combinan con AND entre sí; dentro de ``filter``
        se combinan con OR):
        - ``filter``   : cadena opcional que busca por icontains en titulo,
                         autor e isbn (OR entre los tres campos).
        - ``categoria``: id opcional de categoría, filtra por id_categoria (exacto).
        - Si no se pasa ningún filtro se devuelven todos los libros activos.
        La paginación es de 10 elementos por página y devuelve el envelope
        con maxPages/currentpage/previous/next.
        """
        page = request.GET.get('page')
        pagesize = 10
        filter = request.GET.get('filter')
        categoria = request.GET.get('categoria')

        if filter or categoria:
            query = Q()

            if filter:
                query |= Q(titulo__icontains=filter) | \
                         Q(autor__icontains=filter) | \
                         Q(isbn__icontains=filter)

            if categoria:
                try:
                    categoria = int(categoria)
                except (ValueError, TypeError):
                    return Result.Error("El parámetro categoria debe ser un número entero")
                query &= Q(id_categoria=categoria)

            cont = Libro.objects.filter(activo=True).filter(query).order_by('id_libro')

        else:
            cont = Libro.objects.filter(activo=True).order_by('id_libro')

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

        serialdata = LibroSerializer(page_obj, many=True)

        return Result.ResponsePaginator('', serialdata.data, total_pages, page, button_previous, button_next)

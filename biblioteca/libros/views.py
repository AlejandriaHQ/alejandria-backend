from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q, ProtectedError
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter

from ..models import Libro
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


@extend_schema(tags=['libros'])
class LibroViewSet(viewsets.ModelViewSet):
    queryset = Libro.objects.all()
    serializer_class = LibroSerializer
    http_method_names = ['get', 'post', 'put', 'delete']

    @extend_schema(
        description="Obtener la lista de libros",
        responses={200: OpenApiTypes.OBJECT})
    def list(self, request):
        libros = Libro.objects.all()
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

        try:
            libro.delete()
        except ProtectedError:
            return Result.Error("No se puede eliminar: el libro tiene prestamos asociados")

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

        button_previous = page > 1
        button_next = page < total_pages

        serialdata = LibroSerializer(page_obj, many=True)

        return Result.ResponsePaginator('', serialdata.data, total_pages, page, button_previous, button_next)

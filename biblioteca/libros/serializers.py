import re

from rest_framework import serializers
from ..models import Libro

#Libro Serializer

# Validación de formato ISBN (RN-09): se acepta un ISBN-10 (9 dígitos + un
# dígito o 'X'/'x' de control) o un ISBN-13 (13 dígitos). Se toleran guiones y
# espacios (formato legible habitual) porque se limpian antes de validar.
# Decisión: validación de FORMATO, no de checksum: el checksum real (algoritmo
# de Luhn/GB/T) descarta ISBNs históricos correctos y complica la captura.
_ISBN_REGEX = re.compile(r'^(?:\d{13}|\d{9}[\dXx])$')


def _validar_formato_isbn(value):
    """Rechaza un ISBN que no sea formato ISBN-10 o ISBN-13 (RN-09)."""
    valor_limpio = value.replace('-', '').replace(' ', '')
    if not _ISBN_REGEX.match(valor_limpio):
        raise serializers.ValidationError("El ISBN no tiene un formato válido")


class LibroSerializer(serializers.ModelSerializer):
    # Campos computados de solo lectura (RF-09): cuántos ejemplares están
    # prestados y cuántos están disponibles. Se calculan a partir de los
    # préstamos activos del libro, no de columnas de la BD.
    prestados = serializers.SerializerMethodField()
    disponibles = serializers.SerializerMethodField()

    class Meta:
        model = Libro
        fields = '__all__'

    def get_prestados(self, obj):
        return obj.prestados()

    def get_disponibles(self, obj):
        return obj.disponibles()


class LibroSerializerReg(serializers.ModelSerializer):
    # isbn se declara explícitamente con validators=[] para desactivar el
    # UniqueValidator automático de DRF (mensaje en inglés) y delegar la
    # detección de duplicados a validate_isbn con un mensaje claro.
    isbn = serializers.CharField(
        max_length=20, allow_blank=True, allow_null=True, required=False, validators=[])

    class Meta:
        model = Libro
        fields = ['id_libro', 'titulo', 'autor', 'isbn', 'cantidad', 'id_categoria',
                  'anio', 'editorial', 'descripcion', 'portada']

    def validate_isbn(self, value):
        # Formato (RN-09) y duplicado con mensaje claro en lugar del genérico
        # "Complete los campos vacios": detecta el duplicado de ISBN antes de
        # que DRF/la BD lo rechace.
        if value:
            _validar_formato_isbn(value)
            if Libro.objects.filter(isbn=value).exists():
                raise serializers.ValidationError("Ya existe un libro con ese ISBN")
        return value


class LibroSerializerUpdate(serializers.ModelSerializer):
    isbn = serializers.CharField(
        max_length=20, allow_blank=True, allow_null=True, required=False, validators=[])

    class Meta:
        model = Libro
        fields = ['id_libro', 'titulo', 'autor', 'isbn', 'cantidad', 'id_categoria',
                  'anio', 'editorial', 'descripcion', 'portada', 'activo']

    def validate_isbn(self, value):
        # Formato (RN-09) y duplicado. En update se excluye el propio
        # registro para que reenviar el mismo ISBN no se considere duplicado.
        if value:
            _validar_formato_isbn(value)
            qs = Libro.objects.filter(isbn=value)
            if self.instance is not None:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError("Ya existe un libro con ese ISBN")
        return value


class LibroSerializerDelete(serializers.ModelSerializer):
    class Meta:
        model = Libro
        fields = ['id_libro']

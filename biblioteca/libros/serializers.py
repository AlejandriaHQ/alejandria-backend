from rest_framework import serializers
from ..models import Libro

#Libro Serializer

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
        # Mensaje claro en lugar del genérico "Complete los campos vacios":
        # detecta el duplicado de ISBN antes de que DRF/la BD lo rechace.
        if value and Libro.objects.filter(isbn=value).exists():
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
        # En update se excluye el propio registro para que reenviar el mismo
        # ISBN no se considere duplicado.
        if value:
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

from rest_framework import serializers
from ..models import Libro

#Libro Serializer

class LibroSerializer(serializers.ModelSerializer):
    class Meta:
        model = Libro
        fields = '__all__'


class LibroSerializerReg(serializers.ModelSerializer):
    # isbn se declara explícitamente con validators=[] para desactivar el
    # UniqueValidator automático de DRF (mensaje en inglés) y delegar la
    # detección de duplicados a validate_isbn con un mensaje claro.
    isbn = serializers.CharField(
        max_length=20, allow_blank=True, allow_null=True, required=False, validators=[])

    class Meta:
        model = Libro
        fields = ['id_libro', 'titulo', 'autor', 'isbn', 'cantidad', 'id_categoria']

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
        fields = ['titulo', 'autor', 'isbn', 'cantidad', 'id_categoria']

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

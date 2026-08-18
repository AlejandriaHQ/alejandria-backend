from rest_framework import serializers
from ..models import Libro

#Libro Serializer

class LibroSerializer(serializers.ModelSerializer):
    class Meta:
        model = Libro
        fields = '__all__'


class LibroSerializerReg(serializers.ModelSerializer):
    class Meta:
        model = Libro
        fields = ['id_libro', 'titulo', 'autor', 'isbn', 'cantidad', 'id_categoria']


class LibroSerializerUpdate(serializers.ModelSerializer):
    class Meta:
        model = Libro
        fields = ['titulo', 'autor', 'isbn', 'cantidad', 'id_categoria']


class LibroSerializerDelete(serializers.ModelSerializer):
    class Meta:
        model = Libro
        fields = ['id_libro']

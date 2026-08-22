from rest_framework import serializers
from ..models import Libro
from ..models import Prestamo

#Libro Serializer

class LibroSerializer(serializers.ModelSerializer):
    disponible = serializers.SerializerMethodField()
    class Meta:
        model = Libro
        fields = ['id_libro', 'titulo', 'autor', 'isbn', 'cantidad', 'id_categoria', 'disponible']
        
        def get_disponible(self, obj):
            prestamo_activo = obj.prestamo_set.filter(devuelto = False).exists()
            return not prestamo_activo


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

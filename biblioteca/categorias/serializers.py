from rest_framework import serializers
from ..models import Categoria

#Categoria Serializer

class CategoriasSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = '__all__'


class CategoriasSerializerReg(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ['id_categoria', 'nombre', 'descripcion', 'activo']


class CategoriasSerializerUpdate(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ['nombre', 'descripcion', 'activo']


class CategoriasSerializerDelete(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ['id_categoria']
from rest_framework import serializers
from ..models import Usuario

#Usuario Serializer

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = '__all__'


class UsuarioSerializerReg(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['id_usuario', 'nombre', 'apellido', 'correo', 'telefono', 'contrasena']


class UsuarioSerializerUpdate(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['nombre', 'apellido', 'correo', 'telefono', 'contrasena']


class UsuarioSerializerDelete(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['id_usuario']

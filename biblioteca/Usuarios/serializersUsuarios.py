from rest_framework import serializers
from ..models import Usuario

#Usuario Serializer

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = '__all__'
        # contrasena es write_only: solo entra por POST/PUT, nunca se devuelve
        extra_kwargs = {
            'contrasena': {'write_only': True},
        }


class UsuarioSerializerReg(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['id_usuario', 'nombre', 'apellido', 'correo', 'telefono', 'contrasena']
        # contrasena write_only: se acepta al crear pero no se devuelve en la respuesta
        extra_kwargs = {
            'contrasena': {'write_only': True},
        }


class UsuarioSerializerUpdate(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['nombre', 'apellido', 'correo', 'telefono', 'contrasena']
        # contrasena write_only: se acepta al actualizar pero no se devuelve en la respuesta
        extra_kwargs = {
            'contrasena': {'write_only': True},
        }


class UsuarioSerializerDelete(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['id_usuario']

from rest_framework import serializers
from ..models import Usuario
from django.contrib.auth.models import User


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
        
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'correo', 'is_staff']

def create(self, validated_data):
    user = User.objects.create_user(
        username=validated_data['username'],
        email=validated_data['correo'],
        password=validated_data['contrasena'],
        first_name=validated_data['nombre'],
        last_name=validated_data['apellido']
    )
    return user
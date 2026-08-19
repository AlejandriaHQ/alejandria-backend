from rest_framework import serializers
from ..models import Usuario

#Usuario Serializer

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = '__all__'
        # password es write_only: solo entra por POST/PUT, nunca se devuelve
        extra_kwargs = {
            'password': {'write_only': True},
        }


class UsuarioSerializerReg(serializers.ModelSerializer):
    # correo se declara explícitamente con validators=[] para desactivar el
    # UniqueValidator automático de DRF (mensaje en inglés) y delegar la
    # detección de duplicados a validate_correo con un mensaje claro.
    correo = serializers.EmailField(max_length=150, validators=[])

    class Meta:
        model = Usuario
        fields = ['id_usuario', 'nombre', 'apellido', 'correo', 'telefono', 'password']
        # password write_only: se acepta al crear pero no se devuelve en la respuesta
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def validate_correo(self, value):
        # Mensaje claro en lugar del genérico "Complete los campos vacios":
        # detecta el duplicado de correo antes de que DRF/la BD lo rechace.
        if Usuario.objects.filter(correo=value).exists():
            raise serializers.ValidationError("Ya existe un usuario con ese correo")
        return value


class UsuarioSerializerUpdate(serializers.ModelSerializer):
    correo = serializers.EmailField(max_length=150, validators=[])

    class Meta:
        model = Usuario
        fields = ['nombre', 'apellido', 'correo', 'telefono', 'password']
        # password write_only y opcional: permite actualizar nombre/correo/
        # telefono sin reenviar la contraseña. Si se envía, el modelo la hashea.
        extra_kwargs = {
            'password': {'write_only': True, 'required': False},
        }

    def validate_correo(self, value):
        # En update se excluye el propio registro para que reenviar el mismo
        # correo no se considere duplicado.
        qs = Usuario.objects.filter(correo=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Ya existe un usuario con ese correo")
        return value

    def update(self, instance, validated_data):
        # Si no se envió nueva contraseña, se quita de validated_data para no
        # pisar el hash existente. Si vino, se deja para que el modelo la
        # hashee en save().
        if 'password' not in validated_data:
            validated_data.pop('password', None)
        return super().update(instance, validated_data)


class UsuarioSerializerDelete(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['id_usuario']

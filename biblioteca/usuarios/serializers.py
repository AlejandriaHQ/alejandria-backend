from rest_framework import serializers
from ..models import Usuario

# F09 pentest: el mensaje de correo duplicado NO debe confirmar que el correo
# ya está registrado, porque eso permite enumerar cuentas existentes. Se usa un
# mensaje genérico (idéntico para CREATE y UPDATE) que no distingue entre
# "correo en uso" y "datos no válidos". Compensación asumida: es menos amigable
# para el usuario legítimo, pero elimina el vector de enumeración de cuentas.
MENSAJE_CORREO_NO_DISPONIBLE = "No se pudo completar la operación. Revise los datos enviados."

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
    # detección de duplicados a validate_correo con un mensaje controlado.
    correo = serializers.EmailField(max_length=150, validators=[])

    class Meta:
        model = Usuario
        fields = ['id_usuario', 'nombre', 'apellido', 'correo', 'telefono', 'password']
        # password write_only: se acepta al crear pero no se devuelve en la respuesta
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def validate_correo(self, value):
        # Se detecta el duplicado antes de que DRF/la BD lo rechace, pero se
        # responde con un mensaje GENÉRICO (F09): "no se pudo completar" no
        # confirma que el correo exista, por lo que no se puede enumerar
        # cuentas registradas. El cliente solo sabe que algo no fue válido.
        if Usuario.objects.filter(correo=value).exists():
            raise serializers.ValidationError(MENSAJE_CORREO_NO_DISPONIBLE)
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
        # correo no se considere duplicado. Mismo mensaje genérico que en
        # create (F09): no revela si el correo pertenece a otra cuenta.
        qs = Usuario.objects.filter(correo=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(MENSAJE_CORREO_NO_DISPONIBLE)
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

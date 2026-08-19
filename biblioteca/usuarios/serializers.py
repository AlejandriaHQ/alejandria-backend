import re

from rest_framework import serializers

from ..models import Usuario

# F09 pentest: el mensaje de correo duplicado NO debe confirmar que el correo
# ya está registrado, porque eso permite enumerar cuentas existentes. Se usa un
# mensaje genérico (idéntico para CREATE y UPDATE) que no distingue entre
# "correo en uso" y "datos no válidos". Aplica igualmente a la cédula: al ser
# un identificador personal, confirmar su existencia también facilita
# enumeración de socios. Compensación asumida: es menos amigable para el
# usuario legítimo, pero elimina el vector de enumeración.
MENSAJE_OPERACION_NO_DISPONIBLE = "No se pudo completar la operación. Revise los datos enviados."

# Formato de cédula dominicana: 000-0000000-0
CEDULA_RE = re.compile(r'^\d{3}-\d{7}-\d{1}$')

#Usuario Serializer

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = [
            'id', 'first_name', 'last_name', 'email', 'phone', 'cedula',
            'address', 'role', 'identifier', 'is_staff', 'is_active',
        ]
        # identifier es autogenerado por el modelo: read_only, no se envía.
        read_only_fields = ['id', 'identifier', 'is_staff', 'is_active']


class UsuarioSerializerReg(serializers.ModelSerializer):
    # email/cedula se declaran explícitamente con validators=[] para desactivar
    # el UniqueValidator automático de DRF (mensaje en inglés) y delegar la
    # detección de duplicados a validate_email/validate_cedula con mensajes
    # controlados (F09).
    email = serializers.EmailField(validators=[])
    cedula = serializers.CharField(max_length=15, required=False, allow_blank=True, allow_null=True, validators=[])

    class Meta:
        model = Usuario
        fields = [
            'id', 'first_name', 'last_name', 'email', 'phone', 'cedula',
            'address', 'role', 'password',
        ]
        # password write_only: se acepta al crear pero no se devuelve.
        extra_kwargs = {
            'password': {'write_only': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
            'role': {'required': False},  # default 'user'
        }

    def validate_email(self, value):
        # Se detecta el duplicado antes de que DRF/la BD lo rechace, pero se
        # responde con un mensaje GENÉRICO (F09): "no se pudo completar" no
        # confirma que el correo exista, por lo que no se puede enumerar
        # cuentas registradas.
        if Usuario.objects.filter(email=value).exists():
            raise serializers.ValidationError(MENSAJE_OPERACION_NO_DISPONIBLE)
        return value

    def validate_cedula(self, value):
        if not value:
            return value
        if not CEDULA_RE.fullmatch(value):
            raise serializers.ValidationError("La cédula debe tener el formato 000-0000000-0")
        if Usuario.objects.filter(cedula=value).exists():
            # Mismo mensaje genérico que el correo (F09): no confirma si la
            # cédula pertenece a otra cuenta.
            raise serializers.ValidationError(MENSAJE_OPERACION_NO_DISPONIBLE)
        return value

    def create(self, validated_data):
        # AbstractUser no hashea el password en save(); se usa set_password.
        password = validated_data.pop('password')
        usuario = Usuario(**validated_data)
        usuario.set_password(password)
        usuario.save()
        return usuario


class UsuarioSerializerUpdate(serializers.ModelSerializer):
    email = serializers.EmailField(validators=[])
    cedula = serializers.CharField(max_length=15, required=False, allow_blank=True, allow_null=True, validators=[])

    class Meta:
        model = Usuario
        fields = [
            'first_name', 'last_name', 'email', 'phone', 'cedula',
            'address', 'role', 'password',
        ]
        # password write_only y opcional: permite actualizar el resto de campos
        # sin reenviar la contraseña. Si se envía, se hashea con set_password.
        extra_kwargs = {
            'password': {'write_only': True, 'required': False},
        }

    def validate_email(self, value):
        # En update se excluye el propio registro para que reenviar el mismo
        # correo no se considere duplicado. Mismo mensaje genérico (F09).
        qs = Usuario.objects.filter(email=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(MENSAJE_OPERACION_NO_DISPONIBLE)
        return value

    def validate_cedula(self, value):
        if not value:
            return value
        if not CEDULA_RE.fullmatch(value):
            raise serializers.ValidationError("La cédula debe tener el formato 000-0000000-0")
        qs = Usuario.objects.filter(cedula=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(MENSAJE_OPERACION_NO_DISPONIBLE)
        return value

    def update(self, instance, validated_data):
        # Si no se envió nueva contraseña, se deja el hash existente; si vino,
        # se hashea con set_password (AbstractUser no lo hace en save()).
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)
        # role -> is_staff se sincroniza en el save() del modelo.
        return super().update(instance, validated_data)


class UsuarioSerializerDelete(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['id']
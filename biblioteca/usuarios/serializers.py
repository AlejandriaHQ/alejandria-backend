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
    """Serializer de LECTURA: expone los datos del socio para el panel admin.

    NO expone password (write_only en los serializers de escritura) ni is_staff
    (el rol admin se expone vía 'role'; is_staff es un detalle interno de
    Django auth que el modelo mantiene sincronizado con role).
    """
    class Meta:
        model = Usuario
        fields = [
            'id', 'first_name', 'last_name', 'email', 'phone', 'cedula',
            'address', 'role', 'identifier', 'is_active',
        ]
        # identifier es autogenerado por el modelo: read_only, no se envía.
        read_only_fields = ['id', 'identifier', 'is_active']


class UsuarioSerializerReg(serializers.ModelSerializer):
    """Serializer de CREACIÓN de usuarios (panel admin).

    - identifier read_only: lo autogenera el modelo (ADM-<año>-<seq> /
      MEM-<año>-<seq>); nunca entra por API y sí se devuelve en la respuesta.
    - role y cedula son obligatorios: el panel admin siempre los envía y el
      frontend los necesita (role define el identifier; cedula es única).
    - password write_only + min_length 6: se hashea con set_password en
      create() porque AbstractUser NO hashea en save().
    """
    # email/cedula se declaran explícitamente con validators=[] para desactivar
    # el UniqueValidator automático de DRF (mensaje en inglés) y delegar la
    # detección de duplicados a validate_email/validate_cedula con mensajes
    # controlados (F09).
    email = serializers.EmailField(validators=[])
    cedula = serializers.CharField(max_length=15, required=True, allow_blank=False, validators=[])

    class Meta:
        model = Usuario
        fields = [
            'id', 'first_name', 'last_name', 'email', 'phone', 'cedula',
            'address', 'role', 'password', 'identifier',
        ]
        # password write_only: se acepta al crear pero no se devuelve.
        extra_kwargs = {
            'password': {
                'write_only': True,
                'required': True,
                'min_length': 6,
                'error_messages': {
                    'min_length': 'La contraseña debe tener al menos 6 caracteres',
                },
            },
            'first_name': {'required': True},
            'last_name': {'required': True},
            'role': {'required': True},
        }
        read_only_fields = ['id', 'identifier']

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
    """Serializer de ACTUALIZACIÓN de usuarios (panel admin).

    DECISIÓN (documentada): el email SÍ es editable en update, con unicidad
    que excluye el propio registro: el panel admin debe poder corregir un
    email mal escrito sin reenviar el resto del formulario como falso
    duplicado. El mensaje genérico (F09) sigue impidiendo enumerar cuentas.
    """
    # email/cedula con validators=[]: mismo patrón que Reg (F09). La unicidad
    # se resuelve en validate_email/validate_cedula excluyendo self.
    email = serializers.EmailField(validators=[])
    cedula = serializers.CharField(max_length=15, required=True, allow_blank=False, validators=[])

    class Meta:
        model = Usuario
        fields = [
            'first_name', 'last_name', 'email', 'phone', 'cedula',
            'address', 'role', 'password',
        ]
        # password write_only y opcional: permite actualizar el resto de campos
        # sin reenviar la contraseña. Si se envía, se hashea con set_password.
        extra_kwargs = {
            'password': {
                'write_only': True,
                'required': False,
                'min_length': 6,
                'error_messages': {
                    'min_length': 'La contraseña debe tener al menos 6 caracteres',
                },
            },
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
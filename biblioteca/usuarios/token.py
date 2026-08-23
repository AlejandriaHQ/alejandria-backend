from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from ..models import Usuario


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Login con email (case-insensitive) O identifier O username + password.

    SimpleJWT expone el campo de credencial con el nombre del USERNAME_FIELD
    del modelo ('email'): el cliente envía {"email": <email|identifier|username>,
    "password": ...}.

    Resuelve la credencial en este orden:
      1) email case-insensitive (el email se guarda tal como se registró);
      2) identifier exacto (formato ADM-<año>-<seq> / MEM-<año>-<seq>);
      3) username (login alternativo "usuario001" del frontend: el username se
         autogenera desde el email al guardar, y auth.service.ts lo acepta como
         credencial de login junto con el identifier real MEM-2026-0001).

    Mensaje de error genérico para credenciales inválidas y cuentas inactivas
    (RN-08): no se revela si la cuenta existe ni si está desactivada (misma
    política anti-enumeración de F09).
    """

    def validate(self, attrs):
        credencial = attrs.get(self.username_field, '')
        password = attrs.get('password', '')

        user = None
        if credencial:
            # 1) email case-insensitive
            user = Usuario.objects.filter(email__iexact=credencial).first()
            if user is None:
                # 2) o identifier exacto (ADM-<año>-<seq> / MEM-<año>-<seq>)
                user = Usuario.objects.filter(identifier=credencial).first()
            if user is None:
                # 3) o username (autogenerado desde el email, p. ej. "usuario001")
                user = Usuario.objects.filter(username=credencial).first()

        # Un solo mensaje genérico cubre: usuario inexistente, contraseña
        # incorrecta y cuenta inactiva (RN-08). No enumera cuentas ni revela
        # el estado de la misma.
        if user is None or not user.is_active or not user.check_password(password):
            raise AuthenticationFailed(
                "Identificador o contraseña incorrectos",
                code='authentication_failed',
            )

        # La validación base de SimpleJWT re-autentica con búsqueda exacta
        # (case-sensitive): se reescribe la credencial con el email canónico
        # para que re-autentique correctamente y genere los tokens.
        attrs[self.username_field] = user.email
        return super().validate(attrs)

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Claims custom: role (lo consume el frontend para la sesión) e
        # identifier (credencial visible del socio). El access token copia
        # estos claims del refresh token (comportamiento de SimpleJWT 5.3+).
        token['role'] = user.role
        token['identifier'] = user.identifier
        return token


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
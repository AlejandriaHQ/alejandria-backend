from rest_framework import serializers

from ..models import SolicitudPrestamo, Usuario, Libro


class SolicitudPrestamoSerializer(serializers.ModelSerializer):
    """Serializer de lectura para solicitudes de préstamo."""
    id_usuario_nombre = serializers.SerializerMethodField()
    id_libro_titulo = serializers.SerializerMethodField()

    class Meta:
        model = SolicitudPrestamo
        fields = [
            'id_solicitud', 'id_usuario', 'id_usuario_nombre',
            'id_libro', 'id_libro_titulo',
            'fecha_solicitud', 'estado', 'fecha_respuesta', 'observaciones',
        ]
        read_only_fields = ['id_solicitud', 'fecha_solicitud', 'fecha_respuesta']

    def get_id_usuario_nombre(self, obj):
        return f"{obj.id_usuario.first_name} {obj.id_usuario.last_name}".strip() or obj.id_usuario.email

    def get_id_libro_titulo(self, obj):
        return obj.id_libro.titulo


class SolicitudPrestamoCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear solicitudes (USR o ADM)."""

    class Meta:
        model = SolicitudPrestamo
        fields = ['id_usuario', 'id_libro', 'observaciones']

    def validate(self, attrs):
        # Validar que el libro existe y está activo
        libro = attrs.get('id_libro')
        if libro and not libro.activo:
            raise serializers.ValidationError(
                {'id_libro': 'El libro no está disponible para solicitar'}
            )
        # Validar que el usuario existe (la FK ya lo valida)
        return attrs


class SolicitudPrestamoUpdateEstadoSerializer(serializers.ModelSerializer):
    """Serializer para actualizar estado (aprobar/rechazar/cancelar)."""

    class Meta:
        model = SolicitudPrestamo
        fields = ['estado', 'observaciones']

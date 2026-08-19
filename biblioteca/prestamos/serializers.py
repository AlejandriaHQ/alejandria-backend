from datetime import date, timedelta

from rest_framework import serializers

from ..models import Prestamo

# F12 pentest: una fecha de préstamo anterior a un año (p.ej. 2025-01-01 con
# 19 meses de antigüedad) o posterior a un año hacia el futuro es casi con
# seguridad un error de captura. Una biblioteca puede registrar préstamos con
# retraso (hasta 1 año) y reservas programadas (hasta 1 año adelante), pero no
# fechas absurdas.
_RANGO_FECHA_PRESTAMO = timedelta(days=365)


def _validar_rango_fecha_prestamo(fecha_prestamo):
    """Rechaza fechas de préstamo fuera de un rango razonable (F12 pentest).

    Se aplica solo al valor ENTRANTE (attrs): los registros históricos ya
    creados no se revalidan al actualizar otros campos.
    """
    hoy = date.today()
    if fecha_prestamo < hoy - _RANGO_FECHA_PRESTAMO:
        raise serializers.ValidationError({
            "fecha_prestamo": "La fecha de préstamo no puede ser anterior a un año"
        })
    if fecha_prestamo > hoy + _RANGO_FECHA_PRESTAMO:
        raise serializers.ValidationError({
            "fecha_prestamo": "La fecha de préstamo no puede ser posterior a un año"
        })
    return fecha_prestamo

#Prestamo Serializer

class PrestamoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prestamo
        fields = '__all__'


class PrestamoSerializerReg(serializers.ModelSerializer):
    class Meta:
        model = Prestamo
        fields = ['id_prestamo', 'id_usuario', 'id_libro', 'fecha_prestamo', 'fecha_devolucion', 'estado']

    def validate(self, attrs):
        return self._validar_fechas(attrs)

    def _validar_fechas(self, attrs):
        fecha_prestamo = attrs.get('fecha_prestamo') or (self.instance.fecha_prestamo if self.instance else None)
        fecha_devolucion = attrs.get('fecha_devolucion')
        if fecha_devolucion and fecha_prestamo and fecha_devolucion < fecha_prestamo:
            raise serializers.ValidationError({
                "fecha_devolucion": "La fecha de devolución no puede ser anterior a la fecha de préstamo"
            })
        # F12 pentest: la fecha de préstamo entrante debe estar en un rango
        # razonable (no anterior a un año ni más de un año hacia el futuro).
        # Solo se valida el valor entrante; los registros históricos no se
        # revalidan al actualizar otros campos.
        if 'fecha_prestamo' in attrs and fecha_prestamo:
            _validar_rango_fecha_prestamo(fecha_prestamo)
        return attrs


class PrestamoSerializerUpdate(serializers.ModelSerializer):
    class Meta:
        model = Prestamo
        fields = ['id_usuario', 'id_libro', 'fecha_prestamo', 'fecha_devolucion', 'estado']

    def validate(self, attrs):
        return self._validar_fechas(attrs)

    def _validar_fechas(self, attrs):
        fecha_prestamo = attrs.get('fecha_prestamo') or (self.instance.fecha_prestamo if self.instance else None)
        fecha_devolucion = attrs.get('fecha_devolucion')
        if fecha_devolucion and fecha_prestamo and fecha_devolucion < fecha_prestamo:
            raise serializers.ValidationError({
                "fecha_devolucion": "La fecha de devolución no puede ser anterior a la fecha de préstamo"
            })
        # F12 pentest: la fecha de préstamo entrante debe estar en un rango
        # razonable (no anterior a un año ni más de un año hacia el futuro).
        # Solo se valida el valor entrante; los registros históricos no se
        # revalidan al actualizar otros campos.
        if 'fecha_prestamo' in attrs and fecha_prestamo:
            _validar_rango_fecha_prestamo(fecha_prestamo)
        return attrs


class PrestamoSerializerDelete(serializers.ModelSerializer):
    class Meta:
        model = Prestamo
        fields = ['id_prestamo']

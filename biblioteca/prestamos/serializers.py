from datetime import date, timedelta

from rest_framework import serializers

from ..models import Prestamo

# RN-01 / RF-18: la duración máxima de un préstamo es de 7 días. Se descartó
# la antigua validación de rango ±365 días (F12 pentest sobre el modelo previo
# de préstamos sin tope): con préstamos de plazo reglamentario fijo, el tope
# relevante es la DURACIÓN (fecha_devolucion - fecha_prestamo <= 7 días), no un
# rango absoluto sobre la fecha de préstamo. Un préstamo histórico (antiguo)
# sigue siendo válido: se vuelve Atrasado cuando su vencimiento pasa.
_DIAS_PRESTAMO = Prestamo.DIAS_PRESTAMO  # 7

#Prestamo Serializer

class PrestamoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prestamo
        fields = '__all__'


class PrestamoSerializerReg(serializers.ModelSerializer):
    """Serializer de CREACIÓN de préstamos (panel admin).

    - ``fecha_vencimiento`` es read_only: se calcula en ``create()`` como
      ``fecha_prestamo + 7 días`` (RN-01), nunca la envía el cliente.
    - ``fecha_devolucion`` (esperada) es opcional pero, si llega, no puede ser
      anterior a fecha_prestamo ni superar los 7 días reglamentarios (RN-01).
    """
    class Meta:
        model = Prestamo
        fields = [
            'id_prestamo', 'id_usuario', 'id_libro', 'fecha_prestamo',
            'fecha_vencimiento', 'fecha_devolucion', 'fecha_devolucion_real',
            'devuelto_vencido', 'estado',
        ]
        read_only_fields = ['id_prestamo', 'fecha_vencimiento', 'fecha_devolucion_real', 'devuelto_vencido']

    def validate(self, attrs):
        return self._validar_fechas(attrs)

    def _validar_fechas(self, attrs):
        fecha_prestamo = attrs.get('fecha_prestamo') or (self.instance.fecha_prestamo if self.instance else None)
        fecha_devolucion = attrs.get('fecha_devolucion')
        if fecha_devolucion and fecha_prestamo and fecha_devolucion < fecha_prestamo:
            raise serializers.ValidationError({
                "fecha_devolucion": "La fecha de devolución no puede ser anterior a la fecha de préstamo"
            })
        # RN-01 / RF-18: la duración máxima del préstamo es de 7 días. Si el
        # cliente declara una fecha_devolucion que excede 7 días desde
        # fecha_prestamo se rechaza (antes se validaba un rango absoluto ±365).
        if fecha_devolucion and fecha_prestamo and (fecha_devolucion - fecha_prestamo).days > _DIAS_PRESTAMO:
            raise serializers.ValidationError({
                "fecha_devolucion": "La fecha de devolución no puede superar los 7 días reglamentarios de préstamo"
            })
        return attrs

    def create(self, validated_data):
        # RN-01: la fecha de vencimiento se calcula como fecha_prestamo + 7 días
        # en el momento de la creación del préstamo (respeta la reglamentación).
        validated_data['fecha_vencimiento'] = (
            validated_data['fecha_prestamo'] + timedelta(days=_DIAS_PRESTAMO)
        )
        return super().create(validated_data)


class PrestamoSerializerUpdate(serializers.ModelSerializer):
    """Serializer de ACTUALIZACIÓN de préstamos (panel admin, incluida la
    devolución).

    - ``fecha_vencimiento`` read_only: se recalcula en ``update()`` cuando
      cambia ``fecha_prestamo`` (RN-01).
    - ``fecha_devolucion_real`` y ``devuelto_vencido`` se gestionan en
      ``update()`` al pasar el préstamo a ``Devuelto`` (RF-22 / CU-12).
    """
    class Meta:
        model = Prestamo
        fields = [
            'id_usuario', 'id_libro', 'fecha_prestamo', 'fecha_vencimiento',
            'fecha_devolucion', 'fecha_devolucion_real', 'devuelto_vencido', 'estado',
        ]
        read_only_fields = ['fecha_vencimiento', 'fecha_devolucion_real', 'devuelto_vencido']

    def validate(self, attrs):
        return self._validar_fechas(attrs)

    def _validar_fechas(self, attrs):
        fecha_prestamo = attrs.get('fecha_prestamo') or (self.instance.fecha_prestamo if self.instance else None)
        fecha_devolucion = attrs.get('fecha_devolucion')
        if fecha_devolucion and fecha_prestamo and fecha_devolucion < fecha_prestamo:
            raise serializers.ValidationError({
                "fecha_devolucion": "La fecha de devolución no puede ser anterior a la fecha de préstamo"
            })
        # RN-01 / RF-18: misma regla de duración máxima de 7 días en update.
        if fecha_devolucion and fecha_prestamo and (fecha_devolucion - fecha_prestamo).days > _DIAS_PRESTAMO:
            raise serializers.ValidationError({
                "fecha_devolucion": "La fecha de devolución no puede superar los 7 días reglamentarios de préstamo"
            })
        return attrs

    def update(self, instance, validated_data):
        # RN-01: si cambia la fecha de préstamo se recalcula el vencimiento.
        if 'fecha_prestamo' in validated_data:
            validated_data['fecha_vencimiento'] = (
                validated_data['fecha_prestamo'] + timedelta(days=_DIAS_PRESTAMO)
            )
        # RF-22 / CU-12: al pasar a Devuelto se registra la fecha real de
        # devolución y se marca si fue vencido (sin multa: solo un flag).
        nuevo_estado = validated_data.get('estado', instance.estado)
        if nuevo_estado == Prestamo.ESTADO_DEVUELTO:
            if instance.estado != Prestamo.ESTADO_DEVUELTO:
                vencimiento = validated_data.get('fecha_vencimiento') or instance.fecha_vencimiento
                validated_data['fecha_devolucion_real'] = date.today()
                validated_data['devuelto_vencido'] = bool(vencimiento and date.today() > vencimiento)
        elif instance.estado == Prestamo.ESTADO_DEVUELTO:
            # Se deja de estar devuelto: se limpian los marcadores de devolución.
            validated_data['fecha_devolucion_real'] = None
            validated_data['devuelto_vencido'] = False
        return super().update(instance, validated_data)


class PrestamoSerializerDelete(serializers.ModelSerializer):
    class Meta:
        model = Prestamo
        fields = ['id_prestamo']

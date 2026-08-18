from rest_framework import serializers
from ..models import Prestamo

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
        return attrs


class PrestamoSerializerDelete(serializers.ModelSerializer):
    class Meta:
        model = Prestamo
        fields = ['id_prestamo']

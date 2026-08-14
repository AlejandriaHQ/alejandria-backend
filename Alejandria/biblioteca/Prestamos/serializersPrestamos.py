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


class PrestamoSerializerUpdate(serializers.ModelSerializer):
    class Meta:
        model = Prestamo
        fields = ['id_usuario', 'id_libro', 'fecha_prestamo', 'fecha_devolucion', 'estado']


class PrestamoSerializerDelete(serializers.ModelSerializer):
    class Meta:
        model = Prestamo
        fields = ['id_prestamo']

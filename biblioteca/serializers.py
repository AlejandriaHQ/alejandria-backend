from rest_framework import serializers
from .models import Categoria, Libro, Usuario, Prestamo

#Categoria Serializer

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = '__all__'


class CategoriasSerializerReg(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ['id_categoria', 'nombre', 'descripcion']


class CategoriasSerializerUpdate(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ['nombre', 'descripcion']


class CategoriasSerializerDelete(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ['id_categoria']



#Libro serializer

class LibroSerializer(serializers.ModelSerializer):
    class Meta:
        model = Libro
        fields = '__all__'


class LibroSerializerReg(serializers.ModelSerializer):
    class Meta:
        model = Libro
        fields = ['id_libro', 'titulo', 'autor', 'isbn', 'cantidad', 'id_categoria']

class LibroSerializerUpdate(serializers.ModelSerializer):
    class Meta:
        model = Libro
        fields = ['titulo', 'autor', 'isbn', 'cantidad', 'id_categoria']

class LibroSerializerDelete(serializers.ModelSerializer):
    class Meta:
        model = Libro
        fields = ['id_libro']


##Usuario serializer
class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = '__all__'

class UsuarioSerializerReg(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['id_usuario', 'nombre', 'apellido', 'correo', 'telefono', 'contrasena']

class UsuarioSerializerUpdate(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['nombre', 'apellido', 'correo', 'telefono', 'contrasena']

class UsuarioSerializerDelete(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['id_usuario']


#Prestamo serializer
class PrestamoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prestamo
        fields = '__all__'


class PrestamoSerializerReg(serializers.ModelSerializer):
    class Meta:
        model = Prestamo
        fields = ['id_prestamo', 'id_usuario', 'id_libro', 'fecha_prestamo', 'fecha_devolucion']


class PrestamoSerializerUpdate(serializers.ModelSerializer):
    class Meta:
        model = Prestamo
        fields = ['id_usuario', 'id_libro', 'fecha_prestamo', 'fecha_devolucion']
        

class PrestamoSerializerDelete(serializers.ModelSerializer):
    class Meta:
        model = Prestamo
        fields = ['id_prestamo']
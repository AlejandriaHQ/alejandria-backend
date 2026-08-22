from django.db import models


# MODELO: Categorias
class Categoria(models.Model):
    id_categoria = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'categorias'
        verbose_name_plural = 'Categorías'

    def __str__(self):
        return self.nombre


# MODELO: Libros

class Libro(models.Model):
    id_libro = models.AutoField(primary_key=True)
    titulo = models.CharField(max_length=150)
    autor = models.CharField(max_length=150)
    isbn = models.CharField(max_length=20, unique=True, blank=True, null=True)
    cantidad = models.IntegerField(default=1)
    id_categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,  # No permite eliminar categoría con libros asociados
        db_column='id_categoria'
    )

    class Meta:
        db_table = 'libros'
        verbose_name_plural = 'Libros'

    def __str__(self):
        return f"{self.titulo} - {self.autor}"



# MODELO: Usuarios

class Usuario(models.Model):
    id_usuario = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    correo = models.EmailField(max_length=150, unique=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    contrasena = models.CharField(max_length=255)

    class Meta:
        db_table = 'usuarios'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return f"{self.nombre} {self.apellido}"



# MODELO: Prestamos

class Prestamo(models.Model):
    # Definir estados como constantes
    ESTADO_PRESTADO = 'Prestado'
    ESTADO_DEVUELTO = 'Devuelto'
    ESTADO_ATRASADO = 'Atrasado'
    
    ESTADOS = [
        (ESTADO_PRESTADO, 'Prestado'),
        (ESTADO_DEVUELTO, 'Devuelto'),
        (ESTADO_ATRASADO, 'Atrasado'),
    ]

    id_prestamo = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,  # No permite eliminar usuario con préstamos activos
        db_column='id_usuario'
    )
    id_libro = models.ForeignKey(
        Libro,
        on_delete=models.PROTECT,  # No permite eliminar libro con préstamos activos
        db_column='id_libro'
    )
    fecha_prestamo = models.DateField()
    fecha_devolucion = models.DateField(blank=True, null=True)
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default=ESTADO_PRESTADO
    )
    
    devuelto = models.BooleanField(default=False)
    fecha_devolucion_real = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'prestamos'
        verbose_name_plural = 'Préstamos'

    def __str__(self):
        return f"Préstamo #{self.id_prestamo} - {self.id_usuario} - {self.id_libro}"
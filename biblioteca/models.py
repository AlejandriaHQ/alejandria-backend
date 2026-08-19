from datetime import date
from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.core.validators import MaxValueValidator, MinValueValidator


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
    # F10 pentest: tope superior de ejemplares por título. 10000 es generoso
    # para una biblioteca; por encima de eso es casi con seguridad un error de
    # captura. El tope inferior (>= 1) evita stock negativo o cero.
    cantidad = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(10000)],
    )
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
    password = models.CharField(max_length=255)

    class Meta:
        db_table = 'usuarios'
        verbose_name_plural = 'Usuarios'

    def save(self, *args, **kwargs):
        # Solo se hashea si la contraseña aún no es un hash válido de Django,
        # así se evita re-hashear (y corromper) contraseñas ya almacenadas.
        # Prefijos de hash reconocidos: pbkdf2_, argon2, bcrypt.
        if not self.password.startswith(('pbkdf2_', 'argon2', 'bcrypt')):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

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

    class Meta:
        db_table = 'prestamos'
        verbose_name_plural = 'Préstamos'

    def marcar_atrasado_si_aplica(self):
        # Transición automática Prestado -> Atrasado cuando la fecha de
        # devolución ya venció. NO afecta el stock: solo Prestado -> Devuelto
        # devuelve ejemplares; un préstamo Atrasado mantiene el ejemplar fuera
        # del stock hasta que sea devuelto.
        if self.estado == self.ESTADO_PRESTADO and self.fecha_devolucion and self.fecha_devolucion < date.today():
            self.estado = self.ESTADO_ATRASADO
            self.save(update_fields=['estado'])

    def __str__(self):
        return f"Préstamo #{self.id_prestamo} - {self.id_usuario} - {self.id_libro}"
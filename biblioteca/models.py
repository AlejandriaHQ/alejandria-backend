from datetime import date
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


# MODELO: Categorias
class Categoria(models.Model):
    id_categoria = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    # Eliminación lógica (RN-07 / RF-10): una categoría con libros no se borra
    # físicamente (PROTECT); se desactiva para no romper los libros asociados.
    activo = models.BooleanField(default=True)

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
    # Ficha bibliográfica ampliada (RF-05). Se usa `anio` en español, no `year`.
    anio = models.IntegerField(blank=True, null=True)  # Año de publicación
    editorial = models.CharField(max_length=150, blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    # Decisión del equipo: la portada se guarda por URL (no se sube el archivo).
    portada = models.URLField(max_length=500, blank=True, null=True)
    # Eliminación lógica (RN-06 / RF-07): un libro con préstamos no se borra
    # físicamente, se desactiva para conservar el historial de préstamos.
    activo = models.BooleanField(default=True)
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

    def prestados(self):
        """Cuenta los préstamos ACTIVOS del libro (Prestado o Atrasado).

        No incluye los devueltos: esos ejemplares ya están de vuelta en el
        catálogo. ``Prestamo`` se resuelve en tiempo de ejecución (se define
        más abajo en este mismo módulo), por lo que no hay import circular.
        """
        return Prestamo.objects.filter(
            id_libro=self,
            estado__in=['Prestado', 'Atrasado'],
        ).count()

    def disponibles(self):
        """Ejemplares disponibles = stock total - préstamos activos."""
        return self.cantidad - self.prestados()

    def __str__(self):
        return f"{self.titulo} - {self.autor}"



# MODELO: Usuarios
# Usuario extiende AbstractUser y es el AUTH_USER_MODEL del proyecto
# (settings.AUTH_USER_MODEL = 'biblioteca.Usuario'): los socios hacen login
# real con email + password (JWT). first_name y last_name vienen de
# AbstractUser; se añaden los campos de dominio del socio (phone, cedula,
# address, identifier, role).

class Usuario(AbstractUser):
    # username se autogenera en save() desde el email: AbstractUser lo exige
    # como columna única NOT NULL, aunque el login usa email (USERNAME_FIELD).
    email = models.EmailField(unique=True)  # override: AbstractUser no lo hace unique
    phone = models.CharField(max_length=20, blank=True, null=True)
    # Cédula dominicana con formato 000-0000000-0; el formato lo valida el
    # serializer (el modelo solo la guarda).
    cedula = models.CharField(max_length=15, unique=True, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    # Identificador público autogenerado e inmutable (ADM-<año>-<seq:04d> para
    # admin, MEM-<año>-<seq:04d> para user). El frontend lo usa como
    # credencial visible del socio; nunca se envía al crear/actualizar.
    identifier = models.CharField(max_length=20, unique=True, blank=True, null=True)
    role = models.CharField(
        max_length=10,
        choices=[('admin', 'admin'), ('user', 'user')],
        default='user',
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        # Sin db_table custom: AbstractUser ya usa 'auth_user' (la tabla única
        # de usuarios del framework de auth).
        verbose_name_plural = 'Usuarios'

    def save(self, *args, **kwargs):
        # 1) username obligatorio para AbstractUser: se autogenera desde el
        #    email si viene vacío. El login es por email; el username es solo
        #    un requisito técnico de la columna. Si el email ya fue usado por
        #    otro username, se añade un sufijo numérico hasta hallar uno libre.
        if not self.username:
            base = (self.email or 'usuario').split('@')[0]
            username = base
            contador = 1
            while Usuario.objects.filter(username=username).exists():
                contador += 1
                username = f'{base}{contador}'
            self.username = username

        # 2) identifier inmutable: solo se genera la primera vez (si ya tiene
        #    valor no se regenera). Secuencia: si el registro ya tiene pk se
        #    usa el propio pk (auto-incremento natural de la tabla, único por
        #    definición); si aún no hay pk (primera inserción) se cuentan los
        #    identificadores del mismo prefijo-año y se suma 1. Como el prefijo
        #    incluye el año, dos usuarios de años distintos nunca colisionan.
        if not self.identifier:
            prefijo = 'ADM' if self.role == 'admin' else 'MEM'
            anio = date.today().year
            if self.pk:
                seq = self.pk
            else:
                seq = Usuario.objects.filter(
                    identifier__startswith=f'{prefijo}-{anio}'
                ).count() + 1
            self.identifier = f'{prefijo}-{anio}-{seq:04d}'

        # 3) role e is_staff siempre consistentes. Un superusuario es admin
        #    por definición; is_superuser no se toca (lo maneja createsuperuser).
        if self.is_superuser:
            self.role = 'admin'
            self.is_staff = True
        else:
            self.is_staff = self.role == 'admin'

        # El password lo hashea AbstractUser internamente (set_password /
        # create_user); save() no reimplementa hashing.
        super().save(*args, **kwargs)

    def __str__(self):
        return self.get_full_name() or self.email



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

    # Duración reglamentaria del préstamo (RN-01 / RF-18): 7 días. La fecha
    # de vencimiento se autocalcula como fecha_prestamo + DIAS_PRESTAMO.
    DIAS_PRESTAMO = 7

    id_prestamo = models.AutoField(primary_key=True)
    # FK al AUTH_USER_MODEL (Ahora Usuario es AbstractUser). Se mantiene el
    # atributo Python id_usuario con db_column='id_usuario' para no romper el
    # contrato del frontend, que espera el campo numérico userId/id_usuario en
    # los préstamos. related_name='prestamos' da un acceso inverso claro.
    id_usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,  # No permite eliminar usuario con préstamos activos
        db_column='id_usuario',
        related_name='prestamos',
    )
    id_libro = models.ForeignKey(
        Libro,
        on_delete=models.PROTECT,  # No permite eliminar libro con préstamos activos
        db_column='id_libro'
    )
    fecha_prestamo = models.DateField()
    # Fecha reglamentaria de vencimiento (RN-01 / RF-18): fecha_prestamo + 7
    # días. Se autocalcula en el serializer al crear/actualizar el préstamo
    # (el cliente no la envía: es el due date normativo). Usada para detectar
    # préstamos vencidos (Prestado -> Atrasado) y devoluciones vencidas.
    fecha_vencimiento = models.DateField(blank=True, null=True)
    # Fecha límite de devolución que el cliente/panel declara como esperada
    # (compatibilidad con el contrato actual del frontend). Por RN-01 no puede
    # superar la fecha_vencimiento (7 días). Si el cliente no la envía, el
    # vencimiento normativo es fecha_vencimiento.
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
        # vencimiento ya pasó. La fecha canónica es fecha_vencimiento; para
        # registros creados por fuera del serializer (sin fecha_vencimiento)
        # se cae a fecha_devolucion como límite histórico. NO afecta el stock:
        # solo Prestado -> Devuelto devuelve ejemplares; un préstamo Atrasado
        # mantiene el ejemplar fuera del stock hasta que sea devuelto.
        fecha_limite = self.fecha_vencimiento or self.fecha_devolucion
        if self.estado == self.ESTADO_PRESTADO and fecha_limite and fecha_limite < date.today():
            self.estado = self.ESTADO_ATRASADO
            self.save(update_fields=['estado'])

    def __str__(self):
        return f"Préstamo #{self.id_prestamo} - {self.id_usuario} - {self.id_libro}"
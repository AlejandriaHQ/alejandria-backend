"""
Comando de seed (datos semilla oficiales) de la BD dev.

Crea los usuarios semilla oficiales y un par de datos base de ejemplo de forma
idempotente: si los registros ya existen no los duplica, solo re-fija los
campos para dejarlos consistentes con lo que el frontend espera.

Uso:
    uv run python manage.py seed_data

Regeneración segura: ejecutarlo varias veces no crea duplicados (get_or_create
por email). Los passwords se fijan con set_password (hasheados) en cada corrida,
por lo que un re-seed restaura las credenciales oficiales aunque se hayan
cambiado a mano.

Semilla oficial (coincide con los fallbacks demo del frontend auth.service.ts):
- admin@alejandria.com / admin123          -> role='admin', identifier ADM-2026-0001
- usuario001@alejandria.com / usuario123   -> role='user',  identifier MEM-2026-0001

Decisión (S3): se mantiene este management command como mecanismo de semilla y
NO se crea una data migration. Es más flexible (no se mete en el historial de
migraciones, permite re-seed seguro y se puede ejecutar bajo demanda en cualquier
entorno sin forzar datos en producción), que es lo que necesita el equipo ahora.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from biblioteca.models import Categoria, Libro, Usuario


class Command(BaseCommand):
    help = (
        "Crea los usuarios semilla oficiales y datos base de ejemplo "
        "(idempotente)."
    )

    def handle(self, *args, **options):
        self._seed_usuarios()
        self._seed_catalogo()

    def _crear_o_actualizar_usuario(self, *, email, password, role, first_name,
                                    last_name, cedula, identifier, phone,
                                    address, is_active=True):
        """get_or_create por email + fijar credenciales/campos (idempotente).

        El identifier se fuerza a su valor oficial: como el modelo solo lo
        autogenera cuando viene vacío, al pasarlo con valor se conserva tal cual
        en save(). El password siempre se re-hashea con set_password para que un
        re-seed restaure la credencial oficial tras un cambio manual.
        """
        usuario, creado = Usuario.objects.get_or_create(
            email=email,
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'role': role,
                'cedula': cedula,
                'identifier': identifier,
                'phone': phone,
                'address': address,
                'is_active': is_active,
            },
        )
        # Se re-fijan los campos en cada corrida: un re-seed deja la semilla
        # consistente con lo que espera el frontend aunque se haya editado.
        usuario.first_name = first_name
        usuario.last_name = last_name
        usuario.role = role
        usuario.cedula = cedula
        usuario.identifier = identifier
        usuario.phone = phone
        usuario.address = address
        usuario.is_active = is_active
        # is_staff lo sincroniza el save() del modelo según el role.
        usuario.set_password(password)
        usuario.save()
        return usuario, creado

    @transaction.atomic
    def _seed_usuarios(self):
        admin, admin_creado = self._crear_o_actualizar_usuario(
            email='admin@alejandria.com',
            password='admin123',
            role='admin',
            first_name='Admin',
            last_name='Alejandria',
            cedula='000-0000000-1',
            identifier='ADM-2026-0001',
            phone='809-000-0001',
            address='Calle Alejandría #1',
        )
        self.stdout.write(self.style.SUCCESS(
            f"[{'creado' if admin_creado else 'ya existía'}] "
            f"admin@alejandria.com (identifier={admin.identifier}, "
            f"role={admin.role}, is_staff={admin.is_staff})"
        ))

        miembro, miembro_creado = self._crear_o_actualizar_usuario(
            email='usuario001@alejandria.com',
            password='usuario123',
            role='user',
            first_name='Usuario',
            last_name='Demo',
            cedula='000-0000000-2',
            identifier='MEM-2026-0001',
            phone='809-000-0002',
            address='Calle Demo #2',
        )
        self.stdout.write(self.style.SUCCESS(
            f"[{'creado' if miembro_creado else 'ya existía'}] "
            f"usuario001@alejandria.com (identifier={miembro.identifier}, "
            f"role={miembro.role}, is_staff={miembro.is_staff})"
        ))

    def _seed_catalogo(self):
        """Datos base de ejemplo para probar préstamos (opcional)."""
        categoria, creado = Categoria.objects.get_or_create(
            nombre='Ficción',
            defaults={'descripcion': 'Novelas y obras de ficción.'},
        )
        self.stdout.write(self.style.SUCCESS(
            f"[{'creado' if creado else 'ya existía'}] Categoría: "
            f"{categoria.nombre}"
        ))

        libro, libro_creado = Libro.objects.get_or_create(
            titulo='Cien años de soledad',
            defaults={
                'autor': 'Gabriel García Márquez',
                'isbn': '978-0307474728',
                'cantidad': 5,
                'id_categoria': categoria,
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f"[{'creado' if libro_creado else 'ya existía'}] Libro: "
            f"{libro.titulo} - {libro.autor}"
        ))

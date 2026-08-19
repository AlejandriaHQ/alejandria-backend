"""Tests de autenticación JWT: login por email, identifier y username.

Cubre el contrato de /token/ (CustomTokenObtainPairSerializer): la credencial
se resuelve por email (case-insensitive), por identifier (ADM-/MEM-...) o por
username (el frontend acepta "usuario001", que es el username autogenerado
desde el email), y las credenciales inválidas responden 401 con un mensaje
genérico.
"""
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class LoginTests(APITestCase):
    def setUp(self):
        self.Usuario = get_user_model()
        self.admin = self._crear('admin@alejandria.com', 'admin123', 'admin')
        self.miembro = self._crear('usuario001@alejandria.com', 'usuario123', 'user')

    def _crear(self, email, password, role):
        usuario = self.Usuario(
            email=email,
            role=role,
            first_name='Primer',
            last_name='Apellido',
        )
        # set_password es OBLIGATORIO: AbstractUser no hashea en save().
        usuario.set_password(password)
        usuario.save()
        return usuario

    def _login(self, credencial, password):
        return self.client.post(
            reverse('token_obtain_pair'),
            {'email': credencial, 'password': password},
            format='json',
        )

    def test_login_por_email(self):
        r = self._login('usuario001@alejandria.com', 'usuario123')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn('access', r.data)

    def test_login_por_email_case_insensitive(self):
        r = self._login('USUARIO001@alejandria.com', 'usuario123')
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_login_por_identifier(self):
        r = self._login(self.miembro.identifier, 'usuario123')
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_login_por_username(self):
        # El frontend acepta "usuario001" (username autogenerado desde el email)
        # como credencial de login junto con el identifier real MEM-2026-0001.
        self.assertEqual(self.miembro.username, 'usuario001')
        r = self._login('usuario001', 'usuario123')
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_login_por_email_admin(self):
        r = self._login('admin@alejandria.com', 'admin123')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn('access', r.data)

    def test_login_credencial_invalida(self):
        r = self._login('usuario001@alejandria.com', 'contraseña-incorrecta')
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

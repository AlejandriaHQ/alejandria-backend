from django.urls import path
from . import viewsUsuarios

urlpatterns = [

    #index
    path('', viewsUsuarios.usuarios_list, name='usuarios_list'),

    #usuarios
    path('Usuario_add', viewsUsuarios.Usuario_Add, name='Usuario_add'),
    path('Usuario_update', viewsUsuarios.Usuario_Update, name='Usuario_update'),
    path('Usuario_delete', viewsUsuarios.Usuario_Delete, name='Usuario_delete'),
    path('Usuario_view', viewsUsuarios.Usuario_View, name='Usuario_view'),
    path('Usuario_paginator', viewsUsuarios.Usuario_Paginators, name='Usuario_paginator'),
    
    path('login/', viewsUsuarios.login_view,name='login'),
    path('register/', viewsUsuarios.usuario_registro,name='register'),
]

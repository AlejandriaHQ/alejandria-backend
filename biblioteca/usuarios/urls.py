from django.urls import path
from . import views

urlpatterns = [

    #index
    path('', views.usuarios_list, name='usuarios_list'),

    #usuarios
    path('Usuario_add', views.Usuario_Add, name='Usuario_add'),
    path('Usuario_update', views.Usuario_Update, name='Usuario_update'),
    path('Usuario_delete', views.Usuario_Delete, name='Usuario_delete'),
    path('Usuario_view', views.Usuario_View, name='Usuario_view'),
    path('Usuario_paginator', views.Usuario_Paginators, name='Usuario_paginator'),
]

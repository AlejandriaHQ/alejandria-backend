from django.urls import path
from . import viewsCategorias

urlpatterns = [

    #index
    path('', viewsCategorias.categorias_list, name='categorias_list'),

    #categorias
    path('Categoria_add', viewsCategorias.Categoria_Add, name='Categoria_add'),
    path('Categoria_update', viewsCategorias.Categoria_Update, name='Categoria_update'),
    path('Categoria_delete', viewsCategorias.Categoria_Delete, name='Categoria_delete'),
    path('Categoria_view', viewsCategorias.Categoria_View, name='Categoria_view'),
    path('Categoria_paginator', viewsCategorias.Categoria_Paginators, name='Categoria_paginator'),
]

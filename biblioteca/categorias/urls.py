from django.urls import path
from . import views

urlpatterns = [

    #index
    path('', views.categorias_list, name='categorias_list'),

    #categorias
    path('Categoria_add', views.Categoria_Add, name='Categoria_add'),
    path('Categoria_update', views.Categoria_Update, name='Categoria_update'),
    path('Categoria_delete', views.Categoria_Delete, name='Categoria_delete'),
    path('Categoria_view', views.Categoria_View, name='Categoria_view'),
    path('Categoria_paginator', views.Categoria_Paginators, name='Categoria_paginator'),
]

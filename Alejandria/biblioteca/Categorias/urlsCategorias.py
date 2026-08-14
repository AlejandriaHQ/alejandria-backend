from django.contrib import admin
from django.urls import path
from . import viewsCategorias
from .viewsCategorias import Categoria_Add, Categoria_Update, Categoria_Delete, Categoria_View, Categoria_Paginators

urlpatterns = [

    #index
    path('',viewsCategorias.categorias_list, name="/"),

    #categorias
    path('Categoria_add', viewsCategorias.Categoria_Add, name="/Categoria/add"),
    path('Categoria_update', viewsCategorias.Categoria_Update, name="/Categoria/update"),
    path('Categoria_delete', viewsCategorias.Categoria_Delete, name="/Categoria/delete"),
   # path('eliminados', views.Eliminados, name="/eliminados"),
    path('Categoria_view', viewsCategorias.Categoria_View, name="/Categoria/view"),
    path('Categoria_paginator', viewsCategorias.Categoria_Paginators, name="/Categoria/paginator"),
]

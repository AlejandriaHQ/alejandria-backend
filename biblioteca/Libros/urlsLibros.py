from django.urls import path
from . import viewsLibros

urlpatterns = [

    #index
    path('', viewsLibros.libros_list, name='libros_list'),

    #libros
    path('Libro_add', viewsLibros.Libro_Add, name='Libro_add'),
    path('Libro_update', viewsLibros.Libro_Update, name='Libro_update'),
    path('Libro_delete', viewsLibros.Libro_Delete, name='Libro_delete'),
    path('Libro_view', viewsLibros.Libro_View, name='Libro_view'),
    path('Libro_paginator', viewsLibros.Libro_Paginators, name='Libro_paginator'),
]

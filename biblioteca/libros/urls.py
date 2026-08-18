from django.urls import path
from . import views

urlpatterns = [

    #index
    path('', views.libros_list, name='libros_list'),

    #libros
    path('Libro_add', views.Libro_Add, name='Libro_add'),
    path('Libro_update', views.Libro_Update, name='Libro_update'),
    path('Libro_delete', views.Libro_Delete, name='Libro_delete'),
    path('Libro_view', views.Libro_View, name='Libro_view'),
    path('Libro_paginator', views.Libro_Paginators, name='Libro_paginator'),
]

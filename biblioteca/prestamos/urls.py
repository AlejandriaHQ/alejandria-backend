from django.urls import path
from . import views

urlpatterns = [

    #index
    path('', views.prestamos_list, name='prestamos_list'),

    #prestamos
    path('Prestamo_add', views.Prestamo_Add, name='Prestamo_add'),
    path('Prestamo_update', views.Prestamo_Update, name='Prestamo_update'),
    path('Prestamo_delete', views.Prestamo_Delete, name='Prestamo_delete'),
    path('Prestamo_view', views.Prestamo_View, name='Prestamo_view'),
    path('Prestamo_paginator', views.Prestamo_Paginators, name='Prestamo_paginator'),
]

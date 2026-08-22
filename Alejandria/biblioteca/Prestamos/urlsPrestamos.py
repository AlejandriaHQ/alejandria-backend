from django.urls import path
from . import viewsPrestamos

urlpatterns = [

    #index
    path('', viewsPrestamos.prestamos_list, name='prestamos_list'),

    #prestamos
    path('Prestamo_add', viewsPrestamos.Prestamo_Add, name='Prestamo_add'),
    path('Prestamo_delete', viewsPrestamos.Prestamo_Delete, name='Prestamo_delete'),
    path('Prestamo_view', viewsPrestamos.Prestamo_View, name='Prestamo_view'),
    path('Prestamo_paginator', viewsPrestamos.Prestamo_Paginators, name='Prestamo_paginator'),
    
    path('devolver/<int:id_prestamo>/', viewsPrestamos.Prestamo_Devolver, name='prestamo_devolver'),
    path('historial/', viewsPrestamos.Prestamo_Historial, name='prestamo_historial'),
    path('activos/', viewsPrestamos.Prestamo_Activos, name='prestamo_activos'),
    path('vencidos/', viewsPrestamos.Prestamo_Vencidos, name='prestamo_vencidos'),
]

# listings/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('api/finnviewer/', views.listing_data, name='listing_data'),
    path('', views.index, name='index'),
]

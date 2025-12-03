from django.urls import path
from . import views

urlpatterns = [
     path('myprofile/', views.profile_page, name='myprofile'),    
     path('favouries/',views.favourite_view, name='myfavourites') 

]

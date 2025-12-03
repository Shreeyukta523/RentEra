from django.urls import path
from . import views

urlpatterns = [
     path('myprofile/', views.profile_page, name='myprofile'),    
     path('updatefavourite/', views.updatefavourite, name='updatefavourite'),
     path('checkfavourite/', views.checkfavourite, name='checkfavourite',),
     path('addtofavourite/', views.addtofavourite, name='addtofavourite'),
     path('deletefav/', views.deletefavourite, name='deletefavourite',),

]

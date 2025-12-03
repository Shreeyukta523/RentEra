# rentals/urls.py
from django.urls import path
from . import views
from .views import AIChatView

urlpatterns = [
    path('', views.home, name='home'),
    # path('propertydetails/', views.propertydetails, name='propertydetails'),
    path('contact/', views.contact, name='contact'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.login_view, name='login'),
    path('property/' ,views.property_view, name='property'),
    path('propertydetails/<slug:slug>/', views.propertydetails, name='propertydetails'),
    path('logout-confirm/', views.logout_confirm, name='logout_confirm'),       #actual logout page
    path('activate/<uidb64>/<token>/<role>', views.activate_account, name='activate_account'),  
    path('update-profile-image/', views.update_profile_img, name='update_profile_image'),
    path('property/<slug:slug>/send-request/', views.send_property_request, name='send_property_request'),
    path('request/<int:request_id>/cancel/', views.cancel_property_request, name='cancel_property_request'),
    path('notifications/', views.notifications, name='notifications'),
    path('request/<int:request_id>/<str:action>/', views.manage_request, name='manage_request'),
    path('requests/<int:request_id>/renter_details/', views.renter_details, name='renter_details'),

    path('chat/<int:request_id>/', views.chat_view, name='chat'),
    path('requests/', views.requests_view, name='requests'),
     path('ajax/get-featured-properties/', views.get_featured_properties, name='get_featured_properties'),
    path('api/chat/', AIChatView.as_view(), name='ai_chat_api'),
    path('password_reset/', views.password_reset_request, name='password_reset_otp_request'),
    path('password_reset/done/', views.password_reset_otp_done, name='password_reset_otp_done'),
    path('password_reset/verify/', views.password_reset_verify_otp, name='password_reset_verify_otp'),
    path('password_reset/new/', views.password_reset_new_password, name='password_reset_new_password'),

]


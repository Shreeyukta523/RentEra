from django.urls import path
from . import views

urlpatterns = [
    path('addproperty/', views.add_property, name='addproperty'),
    path('property-success/', views.property_success, name='propertysuccess'),
    path('mydashboard/', views.proprietor_dashboard, name='proprietordashboard'),
    path('payment-cancel/', views.property_cancel, name='propertycancel'),
    path('show-payment/', views.show_payment, name='show_payment'),
    path('delete-property/<slug:slug>/', views.delete_property, name='delete_property'),
    path('restore-property/<int:property_id>/', views.restore_property_request, name='restore_property_request'),
]
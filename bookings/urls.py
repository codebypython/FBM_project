from django.urls import path
from . import views

app_name = 'bookings'

urlpatterns = [
    # Customer views
    path('', views.booking_list_view, name='booking_list'),
    path('<int:booking_id>/', views.booking_detail_view, name='booking_detail'),
    path('create/<int:field_id>/', views.create_booking_view, name='create_booking'),
    path('<int:booking_id>/cancel/', views.cancel_booking_view, name='cancel_booking'),
    
    # Manager views
    path('management/', views.booking_management_view, name='booking_management'),
    path('<int:booking_id>/confirm/', views.confirm_booking_view, name='confirm_booking'),
    path('<int:booking_id>/confirm-payment/', views.confirm_payment_view, name='confirm_payment'),
    path('<int:booking_id>/start/', views.start_booking_view, name='start_booking'),
    path('<int:booking_id>/complete/', views.complete_booking_view, name='complete_booking'),
]

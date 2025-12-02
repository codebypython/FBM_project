from django.urls import path
from . import views

app_name = 'fields'

urlpatterns = [
    # Public views
    path('', views.field_list_view, name='field_list'),
    path('<int:field_id>/', views.field_detail_view, name='field_detail'),
    path('<int:field_id>/availability/', views.get_field_availability, name='field_availability'),
    
    # Management views (for managers and admins)
    path('management/', views.field_management_view, name='field_management'),
    path('management/create/', views.field_create_view, name='field_create'),
    path('management/<int:field_id>/edit/', views.field_edit_view, name='field_edit'),
    path('management/<int:field_id>/delete/', views.field_delete_view, name='field_delete'),
    
    # Pricing management
    path('pricing/', views.pricing_management_view, name='pricing_management'),
    path('pricing/create/', views.pricing_create_view, name='pricing_create'),
    path('pricing/<int:pricing_id>/edit/', views.pricing_edit_view, name='pricing_edit'),
    path('pricing/bulk/', views.bulk_pricing_view, name='bulk_pricing'),
]

from django.urls import path
from . import views, dashboard_views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('dashboard/', views.dashboard_view, name='dashboard'),

    # Notifications
    path('notifications/', views.notification_list_view, name='notifications'),

    # User management (for managers and admins)
    path('users/', views.user_management_view, name='user_management'),
    path('users/<int:user_id>/edit/', views.user_edit_view, name='user_edit'),
    path('users/<int:user_id>/toggle-active/', views.user_toggle_active, name='user_toggle_active'),

    # Manager dashboard and analytics
    path('manager-dashboard/', dashboard_views.manager_dashboard_view, name='manager_dashboard'),
    path('analytics/', dashboard_views.analytics_view, name='analytics'),
]

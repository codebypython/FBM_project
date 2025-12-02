from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, UserProfile, Notification, NotificationPreference


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User Admin"""
    list_display = ['username', 'full_name', 'email', 'role', 'is_active', 'date_joined']
    list_filter = ['role', 'is_active', 'date_joined']
    search_fields = ['username', 'full_name', 'email']
    ordering = ['-date_joined']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Thông tin bổ sung', {
            'fields': ('full_name', 'role', 'phone', 'address', 'date_of_birth'),
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Thông tin bổ sung', {
            'fields': ('full_name', 'email', 'role', 'phone'),
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        elif request.user.role == 'manager':
            # Managers can only see customers and other managers
            return qs.filter(role__in=['customer', 'manager'])
        return qs.none()


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """User Profile Admin"""
    list_display = ['user', 'preferred_field_type', 'get_avatar']
    list_filter = ['preferred_field_type']
    search_fields = ['user__username', 'user__full_name']
    
    def get_avatar(self, obj):
        if obj.avatar:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 50%;" />',
                obj.avatar.url
            )
        return "Không có ảnh"
    
    get_avatar.short_description = 'Avatar'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Notification Admin"""
    list_display = ['title', 'recipient', 'notification_type', 'priority', 'is_read', 'created_at']
    list_filter = ['notification_type', 'priority', 'is_read', 'created_at']
    search_fields = ['title', 'message', 'recipient__full_name', 'recipient__username']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'read_at']
    
    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('recipient', 'title', 'message')
        }),
        ('Phân loại', {
            'fields': ('notification_type', 'priority')
        }),
        ('Trạng thái', {
            'fields': ('is_read', 'read_at')
        }),
        ('Hành động', {
            'fields': ('action_url', 'action_text'),
            'classes': ('collapse',)
        }),
        ('Liên kết', {
            'fields': ('related_object_type', 'related_object_id'),
            'classes': ('collapse',)
        }),
        ('Thời gian', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        elif request.user.role in ['manager', 'admin']:
            return qs
        return qs.filter(recipient=request.user)


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    """Notification Preference Admin"""
    list_display = ['user', 'email_notifications_enabled', 'app_notifications_enabled', 'updated_at']
    search_fields = ['user__full_name', 'user__username']
    
    fieldsets = (
        ('Người dùng', {
            'fields': ('user',)
        }),
        ('Thông báo Email', {
            'fields': (
                'email_booking_confirmed',
                'email_booking_cancelled', 
                'email_booking_reminder',
                'email_payment_reminder',
                'email_promotions',
                'email_system_announcements'
            )
        }),
        ('Thông báo trong App', {
            'fields': (
                'app_booking_confirmed',
                'app_booking_cancelled',
                'app_booking_reminder', 
                'app_payment_reminder',
                'app_promotions',
                'app_system_announcements'
            )
        })
    )
    
    def email_notifications_enabled(self, obj):
        enabled_count = sum([
            obj.email_booking_confirmed,
            obj.email_booking_cancelled,
            obj.email_booking_reminder,
            obj.email_payment_reminder,
            obj.email_promotions,
            obj.email_system_announcements
        ])
        return f"{enabled_count}/6"
    
    email_notifications_enabled.short_description = 'Email kích hoạt'
    
    def app_notifications_enabled(self, obj):
        enabled_count = sum([
            obj.app_booking_confirmed,
            obj.app_booking_cancelled,
            obj.app_booking_reminder,
            obj.app_payment_reminder,
            obj.app_promotions,
            obj.app_system_announcements
        ])
        return f"{enabled_count}/6"
    
    app_notifications_enabled.short_description = 'App kích hoạt'

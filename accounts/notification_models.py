from django.db import models
from django.conf import settings
from django.utils import timezone


class Notification(models.Model):
    """Notification model for system notifications"""
    
    NOTIFICATION_TYPES = (
        ('booking_confirmed', 'Đặt sân được xác nhận'),
        ('booking_cancelled', 'Đặt sân bị hủy'),
        ('booking_reminder', 'Nhắc nhở đặt sân'),
        ('payment_reminder', 'Nhắc nhở thanh toán'),
        ('system_announcement', 'Thông báo hệ thống'),
        ('promotion', 'Khuyến mãi'),
    )
    
    PRIORITY_LEVELS = (
        ('low', 'Thấp'),
        ('normal', 'Bình thường'),
        ('high', 'Cao'),
        ('urgent', 'Khẩn cấp'),
    )
    
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    
    title = models.CharField(max_length=255)
    message = models.TextField()
    
    notification_type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPES,
        default='system_announcement'
    )
    
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_LEVELS,
        default='normal'
    )
    
    is_read = models.BooleanField(default=False)
    
    # Optional: link to related object
    related_object_type = models.CharField(max_length=50, blank=True, null=True)
    related_object_id = models.PositiveIntegerField(blank=True, null=True)
    
    # Action URL (optional)
    action_url = models.URLField(blank=True, null=True)
    action_text = models.CharField(max_length=100, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.recipient.full_name}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    def get_priority_class(self):
        """Get CSS class for priority"""
        priority_classes = {
            'low': 'text-muted',
            'normal': 'text-info',
            'high': 'text-warning',
            'urgent': 'text-danger',
        }
        return priority_classes.get(self.priority, 'text-info')
    
    def get_type_icon(self):
        """Get icon for notification type"""
        type_icons = {
            'booking_confirmed': 'bi-check-circle-fill',
            'booking_cancelled': 'bi-x-circle-fill',
            'booking_reminder': 'bi-alarm',
            'payment_reminder': 'bi-credit-card',
            'system_announcement': 'bi-megaphone',
            'promotion': 'bi-gift',
        }
        return type_icons.get(self.notification_type, 'bi-bell')


class NotificationPreference(models.Model):
    """User notification preferences"""
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )
    
    # Email notifications
    email_booking_confirmed = models.BooleanField(default=True)
    email_booking_cancelled = models.BooleanField(default=True)
    email_booking_reminder = models.BooleanField(default=True)
    email_payment_reminder = models.BooleanField(default=True)
    email_promotions = models.BooleanField(default=False)
    email_system_announcements = models.BooleanField(default=True)
    
    # In-app notifications
    app_booking_confirmed = models.BooleanField(default=True)
    app_booking_cancelled = models.BooleanField(default=True)
    app_booking_reminder = models.BooleanField(default=True)
    app_payment_reminder = models.BooleanField(default=True)
    app_promotions = models.BooleanField(default=True)
    app_system_announcements = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Notification Preference'
        verbose_name_plural = 'Notification Preferences'
    
    def __str__(self):
        return f"Preferences for {self.user.full_name}"

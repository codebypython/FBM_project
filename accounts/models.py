from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone


class User(AbstractUser):
    """Custom User model with role-based permissions"""
    
    USER_ROLES = (
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('customer', 'Customer'),
    )
    
    full_name = models.CharField(
        max_length=255, 
        verbose_name='Họ và tên',
        help_text='Nhập họ và tên đầy đủ'
    )
    
    role = models.CharField(
        max_length=20, 
        choices=USER_ROLES, 
        default='customer',
        verbose_name='Vai trò',
        help_text='Vai trò của người dùng trong hệ thống'
    )
    
    phone = models.CharField(
        max_length=15,
        validators=[RegexValidator(
            regex=r'^\+?1?\d{9,15}$',
            message="Số điện thoại phải có định dạng: '+999999999'. Tối đa 15 số."
        )],
        blank=True,
        null=True,
        verbose_name='Số điện thoại'
    )
    
    address = models.TextField(
        blank=True,
        null=True,
        verbose_name='Địa chỉ'
    )
    
    date_of_birth = models.DateField(
        blank=True,
        null=True,
        verbose_name='Ngày sinh'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Ngày tạo')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Ngày cập nhật')
    
    class Meta:
        verbose_name = 'Người dùng'
        verbose_name_plural = 'Người dùng'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.full_name} ({self.username})"
    
    def is_admin(self):
        """Check if user is admin"""
        return self.role == 'admin'
    
    def is_manager(self):
        """Check if user is manager"""
        return self.role == 'manager'
    
    def is_customer(self):
        """Check if user is customer"""
        return self.role == 'customer'
    
    def can_manage_fields(self):
        """Check if user can manage fields"""
        return self.role in ['admin', 'manager']
    
    def can_manage_users(self):
        """Check if user can manage other users"""
        return self.role in ['admin', 'manager']
    
    def can_book_fields(self):
        """Check if user can book fields"""
        return self.role == 'customer'


class UserProfile(models.Model):
    """Extended profile for users"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        verbose_name='Ảnh đại diện'
    )
    bio = models.TextField(
        blank=True,
        max_length=500,
        verbose_name='Tiểu sử'
    )
    preferred_field_type = models.CharField(
        max_length=10,
        choices=[('5', 'Sân 5'), ('7', 'Sân 7')],
        blank=True,
        null=True,
        verbose_name='Loại sân ưa thích'
    )
    
    class Meta:
        verbose_name = 'Hồ sơ người dùng'
        verbose_name_plural = 'Hồ sơ người dùng'
    
    def __str__(self):
        return f"Profile of {self.user.full_name}"


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
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='Người nhận'
    )
    
    title = models.CharField(max_length=255, verbose_name='Tiêu đề')
    message = models.TextField(verbose_name='Nội dung')
    
    notification_type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPES,
        default='system_announcement',
        verbose_name='Loại thông báo'
    )
    
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_LEVELS,
        default='normal',
        verbose_name='Độ ưu tiên'
    )
    
    is_read = models.BooleanField(default=False, verbose_name='Đã đọc')
    
    # Optional: link to related object
    related_object_type = models.CharField(max_length=50, blank=True, null=True)
    related_object_id = models.PositiveIntegerField(blank=True, null=True)
    
    # Action URL (optional)
    action_url = models.URLField(blank=True, null=True, verbose_name='Link hành động')
    action_text = models.CharField(max_length=100, blank=True, null=True, verbose_name='Text hành động')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Ngày tạo')
    read_at = models.DateTimeField(blank=True, null=True, verbose_name='Ngày đọc')
    
    class Meta:
        verbose_name = 'Thông báo'
        verbose_name_plural = 'Thông báo'
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
        User,
        on_delete=models.CASCADE,
        related_name='notification_preferences',
        verbose_name='Người dùng'
    )
    
    # Email notifications
    email_booking_confirmed = models.BooleanField(default=True, verbose_name='Email xác nhận đặt sân')
    email_booking_cancelled = models.BooleanField(default=True, verbose_name='Email hủy đặt sân')
    email_booking_reminder = models.BooleanField(default=True, verbose_name='Email nhắc nhở đặt sân')
    email_payment_reminder = models.BooleanField(default=True, verbose_name='Email nhắc nhở thanh toán')
    email_promotions = models.BooleanField(default=False, verbose_name='Email khuyến mãi')
    email_system_announcements = models.BooleanField(default=True, verbose_name='Email thông báo hệ thống')
    
    # In-app notifications
    app_booking_confirmed = models.BooleanField(default=True, verbose_name='Thông báo xác nhận đặt sân')
    app_booking_cancelled = models.BooleanField(default=True, verbose_name='Thông báo hủy đặt sân')
    app_booking_reminder = models.BooleanField(default=True, verbose_name='Thông báo nhắc nhở đặt sân')
    app_payment_reminder = models.BooleanField(default=True, verbose_name='Thông báo nhắc nhở thanh toán')
    app_promotions = models.BooleanField(default=True, verbose_name='Thông báo khuyến mãi')
    app_system_announcements = models.BooleanField(default=True, verbose_name='Thông báo hệ thống')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Ngày tạo')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Ngày cập nhật')
    
    class Meta:
        verbose_name = 'Cài đặt thông báo'
        verbose_name_plural = 'Cài đặt thông báo'
    
    def __str__(self):
        return f"Cài đặt thông báo - {self.user.full_name}"

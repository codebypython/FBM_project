from datetime import time

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


def field_image_upload_to(instance, filename):
    """
    Store field images in a per-field folder:
    media/fields/<field_id>/<filename>

    Lưu ý: với sân mới chưa có ID, tạm dùng 'temp'.
    Khi chỉnh sửa lại sau khi đã có ID, đường dẫn sẽ ổn định theo ID.
    """
    field_id = instance.pk or 'temp'
    return f"fields/{field_id}/{filename}"


class FieldType(models.Model):
    """Types of football fields"""
    name = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Tên loại sân'
    )
    
    player_count = models.PositiveIntegerField(
        verbose_name='Số người chơi',
        help_text='Số người chơi tối đa trên sân'
    )
    
    description = models.TextField(
        blank=True,
        verbose_name='Mô tả'
    )
    
    class Meta:
        verbose_name = 'Loại sân'
        verbose_name_plural = 'Loại sân'
        ordering = ['player_count']
    
    def __str__(self):
        return f"Sân {self.player_count} người"


class Field(models.Model):
    """Football field model"""
    
    FIELD_STATUS = (
        ('available', 'Trống'),
        ('booked', 'Đã đặt'),
        ('in_use', 'Đang sử dụng'),
        ('maintenance', 'Bảo trì'),
    )
    
    name = models.CharField(
        max_length=100,
        verbose_name='Tên sân'
    )
    
    field_type = models.ForeignKey(
        FieldType,
        on_delete=models.CASCADE,
        verbose_name='Loại sân'
    )
    
    location = models.CharField(
        max_length=255,
        verbose_name='Vị trí',
        help_text='Vị trí cụ thể của sân trong khu vực'
    )
    
    description = models.TextField(
        blank=True,
        verbose_name='Mô tả'
    )
    
    facilities = models.TextField(
        blank=True,
        verbose_name='Tiện ích',
        help_text='Các tiện ích kèm theo: thay đồ, WC, nước uống...'
    )
    
    image = models.ImageField(
        upload_to=field_image_upload_to,
        blank=True,
        null=True,
        verbose_name='Hình ảnh sân'
    )
    
    layout_image = models.ImageField(
        upload_to=field_image_upload_to,
        blank=True,
        null=True,
        verbose_name='Sơ đồ vị trí'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Hoạt động'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Ngày tạo')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Ngày cập nhật')
    
    class Meta:
        verbose_name = 'Sân bóng'
        verbose_name_plural = 'Sân bóng'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} - {self.field_type}"
    
    def get_current_status(self, date=None, time_slot=None):
        """Get current status of the field"""
        if date is None:
            date = timezone.now().date()
        
        from bookings.models import Booking
        
        # Check if field has any active bookings
        active_bookings = Booking.objects.filter(
            field=self,
            date=date,
            status__in=['confirmed', 'in_progress']
        )
        
        if time_slot:
            active_bookings = active_bookings.filter(time_slot=time_slot)
        
        if active_bookings.exists():
            # Check if any booking is currently in progress
            current_time = timezone.now().time()
            for booking in active_bookings:
                if (booking.time_slot.start_time <= current_time <= booking.time_slot.end_time and 
                    booking.status == 'in_progress'):
                    return 'in_use'
            return 'booked'
        
        return 'available'


class TimeSlot(models.Model):
    """Time slots for field bookings"""
    name = models.CharField(
        max_length=50,
        verbose_name='Tên khung giờ'
    )
    
    start_time = models.TimeField(verbose_name='Giờ bắt đầu')
    end_time = models.TimeField(verbose_name='Giờ kết thúc')
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Hoạt động'
    )
    
    class Meta:
        verbose_name = 'Khung giờ'
        verbose_name_plural = 'Khung giờ'
        ordering = ['start_time']
        unique_together = ['start_time', 'end_time']
    
    def __str__(self):
        return f"{self.name} ({self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')})"
    
    def duration_hours(self):
        """Calculate duration in hours"""
        start_datetime = timezone.datetime.combine(timezone.now().date(), self.start_time)
        end_datetime = timezone.datetime.combine(timezone.now().date(), self.end_time)
        
        # Handle case where end time is next day
        if self.end_time < self.start_time:
            end_datetime += timezone.timedelta(days=1)
        
        duration = end_datetime - start_datetime
        return duration.total_seconds() / 3600


class FieldPricing(models.Model):
    """Pricing for fields by time slot and field type"""
    field_type = models.ForeignKey(
        FieldType,
        on_delete=models.CASCADE,
        verbose_name='Loại sân'
    )
    
    time_slot = models.ForeignKey(
        TimeSlot,
        on_delete=models.CASCADE,
        verbose_name='Khung giờ'
    )
    
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='Giá thuê (VNĐ)'
    )
    
    weekend_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
        verbose_name='Giá cuối tuần (VNĐ)'
    )
    
    effective_date = models.DateField(
        default=timezone.now,
        verbose_name='Ngày hiệu lực'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Hoạt động'
    )
    
    class Meta:
        verbose_name = 'Bảng giá'
        verbose_name_plural = 'Bảng giá'
        ordering = ['field_type', 'time_slot']
        unique_together = ['field_type', 'time_slot', 'effective_date']
    
    def __str__(self):
        return f"{self.field_type} - {self.time_slot} - {self.price:,.0f} VNĐ"
    
    def get_price_for_date(self, date):
        """Get price for specific date (weekend vs weekday)"""
        # Weekend is Saturday (5) and Sunday (6)
        if date.weekday() >= 5 and self.weekend_price:
            return self.weekend_price
        return self.price

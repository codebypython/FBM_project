from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone
from fields.models import Field, TimeSlot


class Booking(models.Model):
    """Booking model for field reservations"""
    
    BOOKING_STATUS = (
        ('pending', 'Chờ xác nhận'),
        ('confirmed', 'Đã xác nhận'),
        ('in_progress', 'Đang diễn ra'),
        ('completed', 'Hoàn thành'),
        ('cancelled', 'Đã hủy'),
    )
    
    PAYMENT_STATUS = (
        ('pending', 'Chờ thanh toán'),
        ('paid', 'Đã thanh toán'),
        ('refunded', 'Đã hoàn tiền'),
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Người đặt'
    )
    
    field = models.ForeignKey(
        Field,
        on_delete=models.CASCADE,
        verbose_name='Sân bóng'
    )
    
    time_slot = models.ForeignKey(
        TimeSlot,
        on_delete=models.CASCADE,
        verbose_name='Khung giờ'
    )
    
    date = models.DateField(verbose_name='Ngày đặt sân')
    
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='Tổng tiền (VNĐ)'
    )
    
    deposit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=0,
        verbose_name='Tiền cọc (VNĐ)'
    )
    
    status = models.CharField(
        max_length=20,
        choices=BOOKING_STATUS,
        default='pending',
        verbose_name='Trạng thái đặt sân'
    )
    
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS,
        default='pending',
        verbose_name='Trạng thái thanh toán'
    )
    
    customer_name = models.CharField(
        max_length=255,
        verbose_name='Tên khách hàng',
        help_text='Tên người sẽ sử dụng sân'
    )
    
    customer_phone = models.CharField(
        max_length=15,
        verbose_name='Số điện thoại liên hệ'
    )
    
    note = models.TextField(
        blank=True,
        verbose_name='Ghi chú',
        help_text='Yêu cầu đặc biệt hoặc ghi chú thêm'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Ngày tạo')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Ngày cập nhật')
    
    # Manager fields
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='confirmed_bookings',
        verbose_name='Được xác nhận bởi'
    )
    
    confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Thời gian xác nhận'
    )
    
    cancellation_reason = models.TextField(
        blank=True,
        verbose_name='Lý do hủy'
    )
    
    class Meta:
        verbose_name = 'Đặt sân'
        verbose_name_plural = 'Đặt sân'
        ordering = ['-created_at']
        unique_together = ['field', 'date', 'time_slot']
    
    def __str__(self):
        return f"{self.field.name} - {self.date} - {self.time_slot.name} - {self.customer_name}"
    
    def can_cancel(self):
        """Check if booking can be cancelled"""
        if self.status in ['completed', 'cancelled']:
            return False
        
        # Can't cancel if booking is today and time has passed
        now = timezone.now()
        booking_datetime = timezone.datetime.combine(self.date, self.time_slot.start_time)
        booking_datetime = timezone.make_aware(booking_datetime)
        
        return booking_datetime > now
    
    def can_confirm(self):
        """Check if booking can be confirmed"""
        return self.status == 'pending'
    
    def can_confirm_payment(self):
        """Check if payment can be confirmed"""
        # Can confirm payment if booking is confirmed and payment is pending
        return self.status == 'confirmed' and self.payment_status == 'pending'
    
    def can_start(self):
        """Check if booking can be started"""
        if self.status != 'confirmed':
            return False
        
        # Must have payment confirmed before starting
        if self.payment_status != 'paid':
            return False
        
        now = timezone.now()
        booking_date = self.date
        start_time = self.time_slot.start_time
        
        # Allow starting 15 minutes before scheduled time
        booking_datetime = timezone.datetime.combine(booking_date, start_time)
        booking_datetime = timezone.make_aware(booking_datetime)
        early_start = booking_datetime - timezone.timedelta(minutes=15)
        
        return now >= early_start
    
    def is_overdue(self):
        """Check if booking is overdue"""
        if self.status not in ['confirmed', 'in_progress']:
            return False
        
        now = timezone.now()
        end_datetime = timezone.datetime.combine(self.date, self.time_slot.end_time)
        end_datetime = timezone.make_aware(end_datetime)
        
        return now > end_datetime
    
    def get_remaining_amount(self):
        """Get remaining amount to pay"""
        return self.total_price - self.deposit
    
    def save(self, *args, **kwargs):
        # Auto-update confirmed_at when status changes to confirmed
        if self.status == 'confirmed' and not self.confirmed_at:
            self.confirmed_at = timezone.now()
        
        super().save(*args, **kwargs)


class BookingHistory(models.Model):
    """History of booking status changes"""
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='history'
    )
    
    status = models.CharField(
        max_length=20,
        choices=Booking.BOOKING_STATUS
    )
    
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    comment = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Lịch sử đặt sân'
        verbose_name_plural = 'Lịch sử đặt sân'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.booking} - {self.status} - {self.created_at}"

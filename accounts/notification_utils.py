from django.urls import reverse
from django.utils import timezone

from .models import Notification, NotificationPreference


def create_notification(
    recipient,
    title,
    message,
    notification_type='system_announcement',
    priority='normal',
    action_url=None,
    action_text=None,
    related_object=None,
):
    """Create a new notification (respecting user preferences)."""

    # Check user preferences
    try:
        prefs = recipient.notification_preferences
    except NotificationPreference.DoesNotExist:
        # Create default preferences
        prefs = NotificationPreference.objects.create(user=recipient)

    # Check if user wants this type of in-app notification
    pref_field = f'app_{notification_type}'
    if hasattr(prefs, pref_field) and not getattr(prefs, pref_field):
        return None

    # Set related object info if provided
    related_object_type = None
    related_object_id = None
    if related_object:
        related_object_type = related_object.__class__.__name__.lower()
        related_object_id = related_object.id

    notification = Notification.objects.create(
        recipient=recipient,
        title=title,
        message=message,
        notification_type=notification_type,
        priority=priority,
        action_url=action_url,
        action_text=action_text,
        related_object_type=related_object_type,
        related_object_id=related_object_id,
    )

    return notification


def notify_booking_confirmed(booking):
    """Send notification when booking is confirmed"""
    title = f"Đặt sân {booking.field.name} đã được xác nhận"
    message = f"Đơn đặt sân #{booking.id} của bạn đã được xác nhận. " \
              f"Ngày: {booking.date.strftime('%d/%m/%Y')}, " \
              f"Giờ: {booking.time_slot.name}."
    
    action_url = reverse('bookings:booking_detail', args=[booking.id])
    
    create_notification(
        recipient=booking.user,
        title=title,
        message=message,
        notification_type='booking_confirmed',
        priority='high',
        action_url=action_url,
        action_text='Xem chi tiết',
        related_object=booking
    )


def notify_booking_cancelled(booking, reason=''):
    """Send notification when booking is cancelled"""
    title = f"Đặt sân {booking.field.name} đã bị hủy"
    message = f"Đơn đặt sân #{booking.id} của bạn đã bị hủy. " \
              f"Ngày: {booking.date.strftime('%d/%m/%Y')}, " \
              f"Giờ: {booking.time_slot.name}."
    
    if reason:
        message += f" Lý do: {reason}"
    
    action_url = reverse('bookings:booking_detail', args=[booking.id])
    
    create_notification(
        recipient=booking.user,
        title=title,
        message=message,
        notification_type='booking_cancelled',
        priority='high',
        action_url=action_url,
        action_text='Xem chi tiết',
        related_object=booking
    )


def notify_booking_started(booking):
    """Send notification when booking is started (customer is on the field)."""
    title = f"Bắt đầu sử dụng sân {booking.field.name}"
    message = (
        f"Đơn đặt sân #{booking.id} đã được bắt đầu. "
        f"Ngày: {booking.date.strftime('%d/%m/%Y')}, "
        f"Giờ: {booking.time_slot.name}."
    )

    action_url = reverse('bookings:booking_detail', args=[booking.id])

    create_notification(
        recipient=booking.user,
        title=title,
        message=message,
        notification_type='booking_reminder',
        priority='normal',
        action_url=action_url,
        action_text='Xem chi tiết',
        related_object=booking,
    )


def notify_booking_reminder(booking):
    """Send reminder notification before booking time"""
    title = f"Nhắc nhở: Sân {booking.field.name} sắp tới giờ"
    message = f"Đơn đặt sân #{booking.id} của bạn sẽ bắt đầu trong 1 giờ nữa. " \
              f"Ngày: {booking.date.strftime('%d/%m/%Y')}, " \
              f"Giờ: {booking.time_slot.name}. Vui lòng đến đúng giờ!"
    
    action_url = reverse('bookings:booking_detail', args=[booking.id])
    
    create_notification(
        recipient=booking.user,
        title=title,
        message=message,
        notification_type='booking_reminder',
        priority='normal',
        action_url=action_url,
        action_text='Xem chi tiết',
        related_object=booking
    )


def notify_payment_reminder(booking):
    """Send payment reminder notification"""
    remaining = booking.get_remaining_amount()
    
    title = f"Nhắc nhở thanh toán sân {booking.field.name}"
    message = f"Bạn còn {remaining:,.0f} VNĐ chưa thanh toán cho đơn đặt sân #{booking.id}. " \
              f"Vui lòng thanh toán trước ngày {booking.date.strftime('%d/%m/%Y')}."
    
    action_url = reverse('bookings:booking_detail', args=[booking.id])
    
    create_notification(
        recipient=booking.user,
        title=title,
        message=message,
        notification_type='payment_reminder',
        priority='high',
        action_url=action_url,
        action_text='Thanh toán ngay',
        related_object=booking
    )


def notify_new_user_registration(user):
    """Notify managers about new user registration"""
    from .models import User
    
    managers = User.objects.filter(role__in=['manager', 'admin'])
    
    title = "Người dùng mới đăng ký"
    message = f"Có người dùng mới đăng ký: {user.full_name} ({user.email}). " \
              f"Vai trò: {user.get_role_display()}."
    
    action_url = reverse('accounts:user_management')
    
    for manager in managers:
        create_notification(
            recipient=manager,
            title=title,
            message=message,
            notification_type='system_announcement',
            priority='normal',
            action_url=action_url,
            action_text='Xem danh sách người dùng',
            related_object=user
        )


def notify_system_announcement(title, message, recipients=None, priority='normal'):
    """Send system announcement to users"""
    from .models import User
    
    if recipients is None:
        recipients = User.objects.filter(is_active=True)
    
    for user in recipients:
        create_notification(
            recipient=user,
            title=title,
            message=message,
            notification_type='system_announcement',
            priority=priority
        )


def notify_promotion(title, message, recipients=None):
    """Send promotion notification"""
    from .models import User
    
    if recipients is None:
        # Send to customers only by default
        recipients = User.objects.filter(role='customer', is_active=True)
    
    for user in recipients:
        create_notification(
            recipient=user,
            title=title,
            message=message,
            notification_type='promotion',
            priority='normal'
        )


def get_unread_notifications_count(user):
    """Get count of unread notifications for user"""
    return user.notifications.filter(is_read=False).count()


def mark_all_notifications_read(user):
    """Mark all notifications as read for user"""
    user.notifications.filter(is_read=False).update(
        is_read=True,
        read_at=timezone.now(),
    )

from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Booking, BookingHistory
from accounts.notification_utils import (
    notify_booking_cancelled,
    notify_booking_confirmed,
    notify_booking_started,
    notify_payment_reminder,
)
from fields.models import Field, FieldPricing, TimeSlot


@login_required
def create_booking_view(request, field_id):
    """Create new booking"""
    field = get_object_or_404(Field, id=field_id, is_active=True)
    
    if request.method == 'POST':
        date_str = request.POST.get('date')
        time_slot_id = request.POST.get('time_slot')
        customer_name = request.POST.get('customer_name')
        customer_phone = request.POST.get('customer_phone')
        note = request.POST.get('note', '')
        
        # Validate input
        if not all([date_str, time_slot_id, customer_name, customer_phone]):
            messages.error(request, 'Vui lòng điền đầy đủ thông tin.')
            return redirect('fields:field_detail', field_id=field_id)
        
        try:
            booking_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            time_slot = TimeSlot.objects.get(id=time_slot_id, is_active=True)
        except (ValueError, TimeSlot.DoesNotExist):
            messages.error(request, 'Thông tin ngày hoặc khung giờ không hợp lệ.')
            return redirect('fields:field_detail', field_id=field_id)
        
        # Check if date is not in the past
        if booking_date < timezone.now().date():
            messages.error(request, 'Không thể đặt sân cho ngày đã qua.')
            return redirect('fields:field_detail', field_id=field_id)
        
        # Check if time slot is available
        existing_booking = Booking.objects.filter(
            field=field,
            date=booking_date,
            time_slot=time_slot,
            status__in=['pending', 'confirmed', 'in_progress']
        ).exists()
        
        if existing_booking:
            messages.error(request, 'Khung giờ này đã được đặt. Vui lòng chọn khung giờ khác.')
            return redirect('fields:field_detail', field_id=field_id)
        
        # Get pricing
        try:
            pricing = FieldPricing.objects.get(
                field_type=field.field_type,
                time_slot=time_slot,
                is_active=True,
                effective_date__lte=booking_date
            )
            total_price = pricing.get_price_for_date(booking_date)
        except FieldPricing.DoesNotExist:
            messages.error(request, 'Chưa có bảng giá cho khung giờ này.')
            return redirect('fields:field_detail', field_id=field_id)
        
        # Create booking
        booking = Booking.objects.create(
            user=request.user,
            field=field,
            time_slot=time_slot,
            date=booking_date,
            total_price=total_price,
            customer_name=customer_name,
            customer_phone=customer_phone,
            note=note,
            status='pending'
        )
        
        # Create history entry
        BookingHistory.objects.create(
            booking=booking,
            status='pending',
            changed_by=request.user,
            comment='Đơn đặt sân được tạo'
        )

        # Optional: nhắc thanh toán nếu có tiền cọc/tổng tiền lớn
        if booking.get_remaining_amount() > 0:
            notify_payment_reminder(booking)
        
        messages.success(request, 'Đặt sân thành công! Đơn đặt sân của bạn đang chờ xác nhận.')
        return redirect('bookings:booking_detail', booking_id=booking.id)
    
    return redirect('fields:field_detail', field_id=field_id)


@login_required
def booking_list_view(request):
    """List user's bookings"""
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    
    if request.user.is_customer():
        bookings = Booking.objects.filter(user=request.user)
    elif request.user.is_manager() or request.user.is_admin():
        bookings = Booking.objects.all()
    else:
        bookings = Booking.objects.none()
    
    # Apply filters
    if search_query:
        bookings = bookings.filter(
            Q(customer_name__icontains=search_query) |
            Q(customer_phone__icontains=search_query) |
            Q(field__name__icontains=search_query)
        )
    
    if status_filter:
        bookings = bookings.filter(status=status_filter)
    
    bookings = bookings.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(bookings, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'booking_statuses': Booking.BOOKING_STATUS,
    }
    return render(request, 'bookings/booking_list.html', context)


@login_required
def booking_detail_view(request, booking_id):
    """Booking detail view"""
    if request.user.is_customer():
        booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    elif request.user.is_manager() or request.user.is_admin():
        booking = get_object_or_404(Booking, id=booking_id)
    else:
        messages.error(request, 'Bạn không có quyền xem thông tin này.')
        return redirect('bookings:booking_list')
    
    # Get booking history
    history = booking.history.all().order_by('-created_at')
    
    context = {
        'booking': booking,
        'history': history,
    }
    return render(request, 'bookings/booking_detail.html', context)


@require_POST
@login_required
def cancel_booking_view(request, booking_id):
    """Cancel booking"""
    if request.user.is_customer():
        booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    elif request.user.is_manager() or request.user.is_admin():
        booking = get_object_or_404(Booking, id=booking_id)
    else:
        return JsonResponse({'success': False, 'message': 'Không có quyền thực hiện.'})
    
    if not booking.can_cancel():
        return JsonResponse({'success': False, 'message': 'Không thể hủy đơn đặt sân này.'})
    
    cancellation_reason = request.POST.get('reason', 'Khách hàng hủy đơn')
    
    booking.status = 'cancelled'
    booking.cancellation_reason = cancellation_reason
    booking.save()
    
    # Create history entry
    BookingHistory.objects.create(
        booking=booking,
        status='cancelled',
        changed_by=request.user,
        comment=f'Đơn đặt sân bị hủy: {cancellation_reason}'
    )

    # Thông báo cho khách hàng
    notify_booking_cancelled(booking, cancellation_reason)
    
    return JsonResponse({'success': True, 'message': 'Đã hủy đơn đặt sân thành công.'})


def is_manager_or_admin(user):
    """Check if user is manager or admin"""
    return user.is_authenticated and (user.is_manager() or user.is_admin())


@require_POST
@user_passes_test(is_manager_or_admin)
def confirm_booking_view(request, booking_id):
    """Confirm booking (for managers)"""
    booking = get_object_or_404(Booking, id=booking_id)
    
    if not booking.can_confirm():
        return JsonResponse({'success': False, 'message': 'Không thể xác nhận đơn đặt sân này.'})
    
    booking.status = 'confirmed'
    booking.confirmed_by = request.user
    booking.confirmed_at = timezone.now()
    booking.save()
    
    # Create history entry
    BookingHistory.objects.create(
        booking=booking,
        status='confirmed',
        changed_by=request.user,
        comment=f'Đơn đặt sân được xác nhận bởi {request.user.full_name}'
    )

    # Thông báo xác nhận cho khách hàng
    notify_booking_confirmed(booking)
    
    return JsonResponse({'success': True, 'message': 'Đã xác nhận đơn đặt sân thành công.'})


@require_POST
@user_passes_test(is_manager_or_admin)
def confirm_payment_view(request, booking_id):
    """Confirm payment (for cash payments)"""
    booking = get_object_or_404(Booking, id=booking_id)
    
    if not booking.can_confirm_payment():
        return JsonResponse({'success': False, 'message': 'Không thể xác nhận thanh toán cho đơn đặt sân này.'})
    
    booking.payment_status = 'paid'
    booking.save()
    
    # Create history entry
    BookingHistory.objects.create(
        booking=booking,
        status=booking.status,
        changed_by=request.user,
        comment=f'Xác nhận thanh toán bằng tiền mặt - {request.user.full_name}'
    )

    # Nhắc lại trạng thái thanh toán đã hoàn tất
    title_message = f"Thanh toán đơn đặt sân #{booking.id} đã được xác nhận."
    notify_payment_reminder(booking)
    
    return JsonResponse({'success': True, 'message': 'Đã xác nhận thanh toán thành công.'})


@require_POST
@user_passes_test(is_manager_or_admin)
def start_booking_view(request, booking_id):
    """Start booking (mark as in progress)"""
    booking = get_object_or_404(Booking, id=booking_id)
    
    if not booking.can_start():
        return JsonResponse({'success': False, 'message': 'Không thể bắt đầu sử dụng sân lúc này.'})
    
    booking.status = 'in_progress'
    booking.save()
    
    # Create history entry
    BookingHistory.objects.create(
        booking=booking,
        status='in_progress',
        changed_by=request.user,
        comment=f'Bắt đầu sử dụng sân - {request.user.full_name}'
    )

    # Thông báo bắt đầu sử dụng sân cho khách
    notify_booking_started(booking)
    
    return JsonResponse({'success': True, 'message': 'Đã bắt đầu sử dụng sân.'})


@require_POST
@user_passes_test(is_manager_or_admin)
def complete_booking_view(request, booking_id):
    """Complete booking"""
    booking = get_object_or_404(Booking, id=booking_id)
    
    if booking.status not in ['confirmed', 'in_progress']:
        return JsonResponse({'success': False, 'message': 'Không thể hoàn thành đơn đặt sân này.'})
    
    booking.status = 'completed'
    booking.payment_status = 'paid'  # Assume payment is completed
    booking.save()
    
    # Create history entry
    BookingHistory.objects.create(
        booking=booking,
        status='completed',
        changed_by=request.user,
        comment=f'Đơn đặt sân hoàn thành - {request.user.full_name}'
    )
    
    return JsonResponse({'success': True, 'message': 'Đã hoàn thành đơn đặt sân.'})


@user_passes_test(is_manager_or_admin)
def booking_management_view(request):
    """Booking management dashboard for managers"""
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    date_filter = request.GET.get('date', '')
    
    bookings = Booking.objects.all()
    
    # Apply filters
    if search_query:
        bookings = bookings.filter(
            Q(customer_name__icontains=search_query) |
            Q(customer_phone__icontains=search_query) |
            Q(field__name__icontains=search_query)
        )
    
    if status_filter:
        bookings = bookings.filter(status=status_filter)
    
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            bookings = bookings.filter(date=filter_date)
        except ValueError:
            pass
    
    bookings = bookings.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(bookings, 30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics
    today_bookings = Booking.objects.filter(date=timezone.now().date())
    stats = {
        'total_bookings': bookings.count(),
        'today_bookings': today_bookings.count(),
        'pending_bookings': bookings.filter(status='pending').count(),
        'confirmed_bookings': bookings.filter(status='confirmed').count(),
    }
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'date_filter': date_filter,
        'booking_statuses': Booking.BOOKING_STATUS,
        'stats': stats,
    }
    return render(request, 'bookings/booking_management.html', context)

from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import timedelta, datetime
from decimal import Decimal

from .models import User
from fields.models import Field, FieldType
from bookings.models import Booking


def is_manager_or_admin(user):
    """Check if user is manager or admin"""
    return user.is_authenticated and (user.is_manager() or user.is_admin())


@user_passes_test(is_manager_or_admin)
def manager_dashboard_view(request):
    """Manager dashboard with comprehensive statistics"""
    
    # Date ranges
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    this_week_start = today - timedelta(days=today.weekday())
    this_month_start = today.replace(day=1)
    last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
    last_month_end = this_month_start - timedelta(days=1)
    
    # Overall Statistics
    total_users = User.objects.count()
    total_customers = User.objects.filter(role='customer').count()
    total_managers = User.objects.filter(role='manager').count()
    total_fields = Field.objects.filter(is_active=True).count()
    
    # Booking Statistics
    total_bookings = Booking.objects.count()
    today_bookings = Booking.objects.filter(date=today).count()
    this_week_bookings = Booking.objects.filter(date__gte=this_week_start).count()
    this_month_bookings = Booking.objects.filter(date__gte=this_month_start).count()
    
    # Revenue Statistics
    total_revenue = Booking.objects.filter(
        payment_status='paid'
    ).aggregate(total=Sum('total_price'))['total'] or Decimal('0')
    
    this_month_revenue = Booking.objects.filter(
        date__gte=this_month_start,
        payment_status='paid'
    ).aggregate(total=Sum('total_price'))['total'] or Decimal('0')
    
    last_month_revenue = Booking.objects.filter(
        date__gte=last_month_start,
        date__lte=last_month_end,
        payment_status='paid'
    ).aggregate(total=Sum('total_price'))['total'] or Decimal('0')
    
    # Revenue growth calculation
    revenue_growth = 0
    if last_month_revenue > 0:
        revenue_growth = ((this_month_revenue - last_month_revenue) / last_month_revenue) * 100
    
    # Status Distribution
    status_stats = Booking.objects.values('status').annotate(
        count=Count('id')
    ).order_by('status')
    
    # Popular Field Types
    popular_field_types = Booking.objects.values(
        'field__field_type__name'
    ).annotate(
        booking_count=Count('id')
    ).order_by('-booking_count')[:5]
    
    # Recent Activities (Last 10 bookings)
    recent_bookings = Booking.objects.select_related(
        'user', 'field', 'time_slot'
    ).order_by('-created_at')[:10]
    
    # Peak Hours Analysis
    peak_hours = Booking.objects.values(
        'time_slot__name',
        'time_slot__start_time'
    ).annotate(
        booking_count=Count('id')
    ).order_by('-booking_count')[:5]
    
    # Top Customers
    top_customers = User.objects.filter(
        role='customer'
    ).annotate(
        booking_count=Count('booking'),
        total_spent=Sum('booking__total_price')
    ).order_by('-booking_count')[:10]
    
    # Field Utilization
    field_utilization = Field.objects.annotate(
        booking_count=Count('booking')
    ).order_by('-booking_count')
    
    # Today's Schedule
    today_schedule = Booking.objects.filter(
        date=today
    ).select_related(
        'field', 'time_slot', 'user'
    ).order_by('time_slot__start_time')
    
    # Pending Actions
    pending_bookings = Booking.objects.filter(status='pending').count()
    overdue_bookings = Booking.objects.filter(
        date__lt=today,
        status__in=['confirmed', 'in_progress']
    ).count()
    
    # Weekly Booking Trend (Last 7 days)
    weekly_trend = []
    for i in range(7):
        date = today - timedelta(days=i)
        count = Booking.objects.filter(date=date).count()
        weekly_trend.append({
            'date': date,
            'count': count,
            'day_name': date.strftime('%A')
        })
    weekly_trend.reverse()
    
    context = {
        # Overall Stats
        'total_users': total_users,
        'total_customers': total_customers,
        'total_managers': total_managers,
        'total_fields': total_fields,
        
        # Booking Stats
        'total_bookings': total_bookings,
        'today_bookings': today_bookings,
        'this_week_bookings': this_week_bookings,
        'this_month_bookings': this_month_bookings,
        
        # Revenue Stats
        'total_revenue': total_revenue,
        'this_month_revenue': this_month_revenue,
        'last_month_revenue': last_month_revenue,
        'revenue_growth': revenue_growth,
        
        # Analysis
        'status_stats': status_stats,
        'popular_field_types': popular_field_types,
        'recent_bookings': recent_bookings,
        'peak_hours': peak_hours,
        'top_customers': top_customers,
        'field_utilization': field_utilization,
        
        # Today's Data
        'today_schedule': today_schedule,
        'pending_bookings': pending_bookings,
        'overdue_bookings': overdue_bookings,
        
        # Trends
        'weekly_trend': weekly_trend,
        
        # Date Info
        'today': today,
        'this_month_start': this_month_start,
    }
    
    return render(request, 'accounts/manager_dashboard.html', context)


@user_passes_test(is_manager_or_admin)
def analytics_view(request):
    """Advanced analytics view for managers"""
    
    # Get date range from request
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if not start_date:
        start_date = timezone.now().date() - timedelta(days=30)
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    if not end_date:
        end_date = timezone.now().date()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Filter bookings by date range
    bookings = Booking.objects.filter(
        date__gte=start_date,
        date__lte=end_date
    )
    
    # Daily revenue trend
    daily_revenue = bookings.filter(
        payment_status='paid'
    ).values('date').annotate(
        revenue=Sum('total_price'),
        booking_count=Count('id')
    ).order_by('date')
    
    # Field type performance
    field_performance = bookings.values(
        'field__field_type__name'
    ).annotate(
        booking_count=Count('id'),
        revenue=Sum('total_price')
    ).order_by('-revenue')
    
    # Time slot analysis
    time_slot_analysis = bookings.values(
        'time_slot__name',
        'time_slot__start_time'
    ).annotate(
        booking_count=Count('id'),
        revenue=Sum('total_price')
    ).order_by('time_slot__start_time')
    
    # Customer analysis
    customer_analysis = bookings.values(
        'user__full_name',
        'user__username'
    ).annotate(
        booking_count=Count('id'),
        total_spent=Sum('total_price')
    ).order_by('-total_spent')[:20]
    
    # Conversion rate (confirmed vs total)
    total_bookings = bookings.count()
    confirmed_bookings = bookings.filter(status__in=['confirmed', 'completed']).count()
    conversion_rate = (confirmed_bookings / total_bookings * 100) if total_bookings > 0 else 0
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'daily_revenue': daily_revenue,
        'field_performance': field_performance,
        'time_slot_analysis': time_slot_analysis,
        'customer_analysis': customer_analysis,
        'total_bookings': total_bookings,
        'confirmed_bookings': confirmed_bookings,
        'conversion_rate': conversion_rate,
        'total_revenue': bookings.filter(payment_status='paid').aggregate(
            total=Sum('total_price')
        )['total'] or Decimal('0'),
    }
    
    return render(request, 'accounts/analytics.html', context)

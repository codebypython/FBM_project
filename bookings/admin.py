from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Booking, BookingHistory


class BookingHistoryInline(admin.TabularInline):
    model = BookingHistory
    extra = 0
    readonly_fields = ['created_at']
    fields = ['status', 'changed_by', 'comment', 'created_at']


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    """Booking Admin"""
    list_display = [
        'field', 
        'customer_name', 
        'date', 
        'time_slot', 
        'status_display',
        'payment_status_display',
        'total_price_display', 
        'created_at'
    ]
    list_filter = ['status', 'payment_status', 'date', 'field__field_type', 'created_at']
    search_fields = ['customer_name', 'customer_phone', 'field__name', 'user__username']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at', 'confirmed_at']
    
    fieldsets = (
        ('Thông tin đặt sân', {
            'fields': ('user', 'field', 'date', 'time_slot')
        }),
        ('Thông tin khách hàng', {
            'fields': ('customer_name', 'customer_phone', 'note')
        }),
        ('Trạng thái và thanh toán', {
            'fields': ('status', 'payment_status', 'total_price', 'deposit')
        }),
        ('Quản lý', {
            'fields': ('confirmed_by', 'confirmed_at', 'cancellation_reason'),
            'classes': ('collapse',)
        }),
        ('Thời gian', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [BookingHistoryInline]
    
    def status_display(self, obj):
        status_colors = {
            'pending': 'orange',
            'confirmed': 'blue',
            'in_progress': 'green',
            'completed': 'gray',
            'cancelled': 'red',
        }
        color = status_colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    
    status_display.short_description = 'Trạng thái'
    
    def payment_status_display(self, obj):
        status_colors = {
            'pending': 'orange',
            'paid': 'green',
            'refunded': 'blue',
        }
        color = status_colors.get(obj.payment_status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_payment_status_display()
        )
    
    payment_status_display.short_description = 'Thanh toán'
    
    def total_price_display(self, obj):
        return f"{obj.total_price:,.0f} VNĐ"
    
    total_price_display.short_description = 'Tổng tiền'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.role == 'admin':
            return qs
        elif request.user.role == 'manager':
            return qs  # Managers can see all bookings
        elif request.user.role == 'customer':
            return qs.filter(user=request.user)
        return qs.none()
    
    def save_model(self, request, obj, form, change):
        # Auto-set confirmed_by when confirming
        if change and obj.status == 'confirmed' and not obj.confirmed_by:
            obj.confirmed_by = request.user
        
        super().save_model(request, obj, form, change)
        
        # Create history entry
        if change:
            BookingHistory.objects.create(
                booking=obj,
                status=obj.status,
                changed_by=request.user,
                comment=f"Trạng thái được cập nhật từ admin bởi {request.user.username}"
            )


@admin.register(BookingHistory)
class BookingHistoryAdmin(admin.ModelAdmin):
    """Booking History Admin"""
    list_display = ['booking', 'status', 'changed_by', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['booking__customer_name', 'booking__field__name']
    ordering = ['-created_at']
    readonly_fields = ['created_at']
    
    def has_add_permission(self, request):
        return False  # Prevent manual creation of history entries
    
    def has_change_permission(self, request, obj=None):
        return False  # History should be read-only

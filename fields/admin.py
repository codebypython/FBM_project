from django.contrib import admin
from django.utils.html import format_html
from .models import FieldType, Field, TimeSlot, FieldPricing


@admin.register(FieldType)
class FieldTypeAdmin(admin.ModelAdmin):
    """Field Type Admin"""
    list_display = ['name', 'player_count', 'description']
    search_fields = ['name']
    ordering = ['player_count']


class FieldPricingInline(admin.TabularInline):
    model = FieldPricing
    extra = 0
    fields = ['time_slot', 'price', 'weekend_price', 'is_active']


@admin.register(Field)
class FieldAdmin(admin.ModelAdmin):
    """Field Admin"""
    list_display = ['name', 'field_type', 'location', 'is_active', 'get_image', 'created_at']
    list_filter = ['field_type', 'is_active', 'created_at']
    search_fields = ['name', 'location']
    ordering = ['name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('name', 'field_type', 'location', 'is_active')
        }),
        ('Mô tả và tiện ích', {
            'fields': ('description', 'facilities')
        }),
        ('Hình ảnh', {
            'fields': ('image', 'layout_image')
        }),
        ('Thời gian', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_image(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="100" height="60" style="object-fit: cover;" />',
                obj.image.url
            )
        return "Không có ảnh"
    
    get_image.short_description = 'Hình ảnh'


@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    """Time Slot Admin"""
    list_display = ['name', 'start_time', 'end_time', 'duration_display', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']
    ordering = ['start_time']
    
    def duration_display(self, obj):
        hours = obj.duration_hours()
        return f"{hours:.1f} giờ"
    
    duration_display.short_description = 'Thời lượng'


@admin.register(FieldPricing)
class FieldPricingAdmin(admin.ModelAdmin):
    """Field Pricing Admin"""
    list_display = [
        'field_type', 
        'time_slot', 
        'price_display', 
        'weekend_price_display', 
        'effective_date', 
        'is_active'
    ]
    list_filter = ['field_type', 'is_active', 'effective_date']
    search_fields = ['field_type__name', 'time_slot__name']
    ordering = ['field_type', 'time_slot__start_time']
    
    def price_display(self, obj):
        return f"{obj.price:,.0f} VNĐ"
    
    price_display.short_description = 'Giá thường'
    
    def weekend_price_display(self, obj):
        if obj.weekend_price:
            return f"{obj.weekend_price:,.0f} VNĐ"
        return "Chưa thiết lập"
    
    weekend_price_display.short_description = 'Giá cuối tuần'

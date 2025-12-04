from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta

from .models import Field, FieldType, TimeSlot, FieldPricing
from bookings.models import Booking


def field_list_view(request):
    """List all available fields"""
    search_query = request.GET.get('search', '')
    field_type_filter = request.GET.get('field_type', '')
    
    fields = Field.objects.filter(is_active=True)
    
    # Apply filters
    if search_query:
        fields = fields.filter(
            Q(name__icontains=search_query) |
            Q(location__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    if field_type_filter:
        fields = fields.filter(field_type_id=field_type_filter)
    
    fields = fields.order_by('name')
    
    # Pagination
    paginator = Paginator(fields, 12)  # 12 fields per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get field types for filter
    field_types = FieldType.objects.all()
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'field_type_filter': field_type_filter,
        'field_types': field_types,
    }
    return render(request, 'fields/field_list.html', context)


def field_detail_view(request, field_id):
    """Field detail view with booking information"""
    field = get_object_or_404(Field, id=field_id, is_active=True)
    
    # Get current date and time in local timezone
    current_datetime = timezone.localtime()
    current_date = current_datetime.date()
    
    # Get selected date (default to today)
    selected_date_str = request.GET.get('date', current_date.strftime('%Y-%m-%d'))
    try:
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    except ValueError:
        selected_date = current_date
    
    # Don't allow booking for past dates
    if selected_date < current_date:
        selected_date = current_date
    
    # Get all time slots
    time_slots = TimeSlot.objects.filter(is_active=True).order_by('start_time')
    
    # Get pricing for this field type
    pricing_data = {}
    for time_slot in time_slots:
        try:
            pricing = FieldPricing.objects.get(
                field_type=field.field_type,
                time_slot=time_slot,
                is_active=True,
                effective_date__lte=selected_date
            )
            pricing_data[time_slot.id] = {
                'price': pricing.get_price_for_date(selected_date),
                'pricing_obj': pricing
            }
        except FieldPricing.DoesNotExist:
            pricing_data[time_slot.id] = {
                'price': 0,
                'pricing_obj': None
            }
    
    # Get existing bookings for selected date
    existing_bookings = Booking.objects.filter(
        field=field,
        date=selected_date,
        status__in=['confirmed', 'in_progress', 'pending']
    ).values_list('time_slot_id', flat=True)
    
    # Create time slot availability data
    time_slot_data = []
    # Get current time in local timezone
    current_time = current_datetime.time()
    
    for time_slot in time_slots:
        is_booked = time_slot.id in existing_bookings
        # A time slot is considered "past" if its end time has already passed
        is_past = (selected_date == current_date and 
                  time_slot.end_time <= current_time)
        
        time_slot_data.append({
            'time_slot': time_slot,
            'is_available': not is_booked and not is_past,
            'is_booked': is_booked,
            'is_past': is_past,
            'price': pricing_data.get(time_slot.id, {}).get('price', 0),
        })
    
    # Generate date options (today + next 30 days)
    date_options = []
    for i in range(31):
        date_option = current_date + timedelta(days=i)
        date_options.append(date_option)
    
    context = {
        'field': field,
        'selected_date': selected_date,
        'time_slot_data': time_slot_data,
        'date_options': date_options,
        'pricing_data': pricing_data,
    }
    return render(request, 'fields/field_detail.html', context)


def get_field_availability(request, field_id):
    """AJAX endpoint to get field availability for a specific date"""
    field = get_object_or_404(Field, id=field_id, is_active=True)
    date_str = request.GET.get('date')
    
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid date format'})
    
    # Get current date and time in local timezone
    current_datetime = timezone.localtime()
    current_date = current_datetime.date()
    
    # Don't allow past dates
    if selected_date < current_date:
        return JsonResponse({'error': 'Cannot book for past dates'})
    
    time_slots = TimeSlot.objects.filter(is_active=True).order_by('start_time')
    existing_bookings = Booking.objects.filter(
        field=field,
        date=selected_date,
        status__in=['confirmed', 'in_progress', 'pending']
    ).values_list('time_slot_id', flat=True)
    
    # Get current time in local timezone
    current_time = current_datetime.time()
    
    slot_data = []
    for time_slot in time_slots:
        is_booked = time_slot.id in existing_bookings
        is_past = (selected_date == current_date and 
                  time_slot.end_time <= current_time)
        
        # Get pricing
        try:
            pricing = FieldPricing.objects.get(
                field_type=field.field_type,
                time_slot=time_slot,
                is_active=True,
                effective_date__lte=selected_date
            )
            price = pricing.get_price_for_date(selected_date)
        except FieldPricing.DoesNotExist:
            price = 0
        
        slot_data.append({
            'id': time_slot.id,
            'name': time_slot.name,
            'start_time': time_slot.start_time.strftime('%H:%M'),
            'end_time': time_slot.end_time.strftime('%H:%M'),
            'is_available': not is_booked and not is_past,
            'is_booked': is_booked,
            'is_past': is_past,
            'price': float(price),
            'price_formatted': f"{price:,.0f} VNĐ",
        })
    
    return JsonResponse({'time_slots': slot_data})


def is_manager_or_admin(user):
    """Check if user is manager or admin"""
    return user.is_authenticated and (user.is_manager() or user.is_admin())


@user_passes_test(is_manager_or_admin)
def field_management_view(request):
    """Field management view for managers and admins"""
    search_query = request.GET.get('search', '')
    field_type_filter = request.GET.get('field_type', '')
    sort = request.GET.get('sort', 'id_asc')
    
    fields = Field.objects.all()
    
    # Apply filters
    if search_query:
        fields = fields.filter(
            Q(name__icontains=search_query) |
            Q(location__icontains=search_query)
        )
    
    if field_type_filter:
        fields = fields.filter(field_type_id=field_type_filter)

    # Sorting
    sort_map = {
        'id_asc': 'id',
        'id_desc': '-id',
        'name_asc': 'name',
        'name_desc': '-name',
        'type_asc': 'field_type__name',
        'type_desc': '-field_type__name',
        'created_asc': 'created_at',
        'created_desc': '-created_at',
    }
    order_by = sort_map.get(sort, 'id')
    fields = fields.order_by(order_by, 'id')
    
    # Pagination
    paginator = Paginator(fields, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    field_types = FieldType.objects.all()
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'field_type_filter': field_type_filter,
        'field_types': field_types,
        'sort': sort,
    }
    return render(request, 'fields/field_management.html', context)


@user_passes_test(is_manager_or_admin)
def pricing_management_view(request):
    """Pricing management view"""
    field_type_filter = request.GET.get('field_type', '')
    
    pricing = FieldPricing.objects.filter(is_active=True)
    
    if field_type_filter:
        pricing = pricing.filter(field_type_id=field_type_filter)
    
    pricing = pricing.order_by('field_type', 'time_slot__start_time')
    
    field_types = FieldType.objects.all()
    time_slots = TimeSlot.objects.filter(is_active=True).order_by('start_time')
    
    context = {
        'pricing': pricing,
        'field_types': field_types,
        'time_slots': time_slots,
        'field_type_filter': field_type_filter,
    }
    return render(request, 'fields/pricing_management.html', context)


@user_passes_test(is_manager_or_admin)
def field_create_view(request):
    """Create new field"""
    from .forms import FieldForm
    
    if request.method == 'POST':
        form = FieldForm(request.POST, request.FILES)
        if form.is_valid():
            field = form.save()
            messages.success(request, f'Tạo sân {field.name} thành công!')
            return redirect('fields:field_management')
        else:
            messages.error(request, 'Có lỗi xảy ra. Vui lòng kiểm tra lại thông tin.')
    else:
        form = FieldForm()
    
    context = {'form': form}
    return render(request, 'fields/field_create.html', context)


@user_passes_test(is_manager_or_admin)
def field_edit_view(request, field_id):
    """Edit existing field"""
    from .forms import FieldForm
    
    field = get_object_or_404(Field, id=field_id)
    
    if request.method == 'POST':
        form = FieldForm(request.POST, request.FILES, instance=field)
        if form.is_valid():
            field = form.save()
            messages.success(request, f'Cập nhật sân {field.name} thành công!')
            return redirect('fields:field_management')
        else:
            messages.error(request, 'Có lỗi xảy ra. Vui lòng kiểm tra lại thông tin.')
    else:
        form = FieldForm(instance=field)
    
    context = {'form': form, 'field': field}
    return render(request, 'fields/field_edit.html', context)


@user_passes_test(is_manager_or_admin)
def field_delete_view(request, field_id):
    """Delete field"""
    field = get_object_or_404(Field, id=field_id)
    
    if request.method == 'POST':
        field_name = field.name
        field.delete()
        messages.success(request, f'Đã xóa sân {field_name}!')
        return redirect('fields:field_management')
    
    context = {'field': field}
    return render(request, 'fields/field_delete.html', context)


@user_passes_test(is_manager_or_admin)
def pricing_create_view(request):
    """Create new pricing"""
    from .forms import FieldPricingForm
    
    if request.method == 'POST':
        form = FieldPricingForm(request.POST)
        if form.is_valid():
            pricing = form.save()
            messages.success(request, 'Tạo bảng giá thành công!')
            return redirect('fields:pricing_management')
        else:
            messages.error(request, 'Có lỗi xảy ra. Vui lòng kiểm tra lại thông tin.')
    else:
        form = FieldPricingForm()
    
    context = {'form': form}
    return render(request, 'fields/pricing_create.html', context)


@user_passes_test(is_manager_or_admin)
def pricing_edit_view(request, pricing_id):
    """Edit existing pricing"""
    from .forms import FieldPricingForm
    
    pricing = get_object_or_404(FieldPricing, id=pricing_id)
    
    if request.method == 'POST':
        form = FieldPricingForm(request.POST, instance=pricing)
        if form.is_valid():
            pricing = form.save()
            messages.success(request, 'Cập nhật bảng giá thành công!')
            return redirect('fields:pricing_management')
        else:
            messages.error(request, 'Có lỗi xảy ra. Vui lòng kiểm tra lại thông tin.')
    else:
        form = FieldPricingForm(instance=pricing)
    
    context = {'form': form, 'pricing': pricing}
    return render(request, 'fields/pricing_edit.html', context)


@user_passes_test(is_manager_or_admin)
def bulk_pricing_view(request):
    """Bulk pricing update"""
    from .forms import BulkPricingForm
    from decimal import Decimal
    
    if request.method == 'POST':
        form = BulkPricingForm(request.POST)
        if form.is_valid():
            field_type = form.cleaned_data['field_type']
            base_price = form.cleaned_data['base_price']
            weekend_multiplier = form.cleaned_data['weekend_multiplier']
            peak_hours = form.cleaned_data['peak_hours']
            peak_multiplier = form.cleaned_data['peak_multiplier']
            effective_date = form.cleaned_data['effective_date']
            
            # Deactivate old pricing
            FieldPricing.objects.filter(
                field_type=field_type,
                effective_date__lt=effective_date
            ).update(is_active=False)
            
            # Create new pricing for all time slots
            created_count = 0
            time_slots = TimeSlot.objects.filter(is_active=True)
            
            for time_slot in time_slots:
                # Calculate price based on conditions
                price = base_price
                weekend_price = base_price * weekend_multiplier
                
                # Apply peak hour multiplier
                if str(time_slot.id) in peak_hours:
                    price = price * peak_multiplier
                    weekend_price = weekend_price * peak_multiplier
                
                # Create or update pricing
                pricing, created = FieldPricing.objects.get_or_create(
                    field_type=field_type,
                    time_slot=time_slot,
                    effective_date=effective_date,
                    defaults={
                        'price': price,
                        'weekend_price': weekend_price,
                        'is_active': True
                    }
                )
                
                if created:
                    created_count += 1
                else:
                    # Update existing
                    pricing.price = price
                    pricing.weekend_price = weekend_price
                    pricing.is_active = True
                    pricing.save()
            
            messages.success(request, f'Đã tạo/cập nhật {created_count} bảng giá cho {field_type.name}!')
            return redirect('fields:pricing_management')
        else:
            messages.error(request, 'Có lỗi xảy ra. Vui lòng kiểm tra lại thông tin.')
    else:
        form = BulkPricingForm()
    
    context = {'form': form}
    return render(request, 'fields/bulk_pricing.html', context)

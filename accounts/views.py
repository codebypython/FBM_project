from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import User, UserProfile
from .forms import CustomUserCreationForm, CustomAuthenticationForm, UserProfileForm, UserManagementForm
from .notification_utils import mark_all_notifications_read


def register_view(request):
    """User registration view"""
    if request.user.is_authenticated:
        return redirect('fields:field_list')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Đăng ký thành công! Bạn có thể đăng nhập ngay bây giờ.')
            return redirect('accounts:login')
        else:
            messages.error(request, 'Có lỗi xảy ra trong quá trình đăng ký. Vui lòng kiểm tra lại thông tin.')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect('fields:field_list')
    
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        
        # Kiểm tra validation cơ bản (trường rỗng)
        if not form.is_valid():
            # Xử lý lỗi validation từng trường
            if 'username' in form.errors:
                error_msg = form.errors['username'][0]
                if 'required' in str(error_msg).lower() or 'bắt buộc' in str(error_msg).lower():
                    messages.error(request, 'Vui lòng nhập tên đăng nhập.')
                else:
                    messages.error(request, f'Lỗi tên đăng nhập: {error_msg}')
            
            if 'password' in form.errors:
                error_msg = form.errors['password'][0]
                if 'required' in str(error_msg).lower() or 'bắt buộc' in str(error_msg).lower():
                    messages.error(request, 'Vui lòng nhập mật khẩu.')
                else:
                    messages.error(request, f'Lỗi mật khẩu: {error_msg}')
            
            # Xử lý lỗi non_field_errors (từ AuthenticationForm.clean())
            if form.non_field_errors():
                for error in form.non_field_errors():
                    error_str = str(error).lower()
                    if 'correct username and password' in error_str or 'tên đăng nhập hoặc mật khẩu' in error_str:
                        messages.error(request, 'Tên đăng nhập hoặc mật khẩu không đúng. Vui lòng kiểm tra lại.')
                    elif 'inactive' in error_str or 'vô hiệu hóa' in error_str:
                        messages.error(request, 'Tài khoản này đã bị vô hiệu hóa. Vui lòng liên hệ quản trị viên.')
                    else:
                        messages.error(request, str(error))
        else:
            # Form hợp lệ, thử authenticate
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(username=username, password=password)
            
            if user is not None:
                if not user.is_active:
                    messages.error(request, 'Tài khoản này đã bị vô hiệu hóa. Vui lòng liên hệ quản trị viên.')
                else:
                    # Đăng nhập thành công
                    login(request, user)
                    messages.success(request, f'Chào mừng {user.full_name}!')
                    
                    # Redirect based on user role
                    next_url = request.GET.get('next', '/')
                    if user.is_manager() or user.is_admin():
                        if next_url == '/':
                            next_url = '/admin/'
                    return redirect(next_url)
            else:
                # Sai username hoặc password (trường hợp này thường đã được xử lý bởi form.clean())
                messages.error(request, 'Tên đăng nhập hoặc mật khẩu không đúng. Vui lòng kiểm tra lại.')
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'accounts/login.html', {'form': form})


@login_required
def logout_view(request):
    """User logout view"""
    logout(request)
    messages.success(request, 'Đã đăng xuất thành công!')
    return redirect('accounts:login')


@login_required
def profile_view(request):
    """User profile view"""
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cập nhật thông tin thành công!')
            return redirect('accounts:profile')
        else:
            messages.error(request, 'Có lỗi xảy ra. Vui lòng kiểm tra lại thông tin.')
    else:
        form = UserProfileForm(instance=profile, user=request.user)
    
    # Get user's booking history
    from bookings.models import Booking
    bookings = Booking.objects.filter(user=request.user).order_by('-created_at')[:5]
    completed_bookings_count = Booking.objects.filter(user=request.user, status='completed').count()
    
    context = {
        'form': form,
        'profile': profile,
        'recent_bookings': bookings,
        'completed_bookings_count': completed_bookings_count,
    }
    return render(request, 'accounts/profile.html', context)


def is_manager_or_admin(user):
    """Check if user is manager or admin"""
    return user.is_authenticated and (user.is_manager() or user.is_admin())


@user_passes_test(is_manager_or_admin)
def user_management_view(request):
    """User management view for managers and admins"""
    search_query = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')
    
    users = User.objects.all()
    
    # Apply filters
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(full_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    if role_filter:
        users = users.filter(role=role_filter)
    
    # Managers can only see customers and other managers
    if request.user.is_manager() and not request.user.is_admin():
        users = users.filter(role__in=['customer', 'manager'])
    
    users = users.order_by('-date_joined')
    
    # Pagination
    paginator = Paginator(users, 20)  # 20 users per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'role_filter': role_filter,
        'user_roles': User.USER_ROLES,
    }
    return render(request, 'accounts/user_management.html', context)


@user_passes_test(is_manager_or_admin)
def user_edit_view(request, user_id):
    """Edit user view for managers and admins"""
    user = get_object_or_404(User, id=user_id)
    
    # Managers cannot edit admin users
    if request.user.is_manager() and not request.user.is_admin():
        if user.is_admin():
            messages.error(request, 'Bạn không có quyền chỉnh sửa tài khoản admin.')
            return redirect('accounts:user_management')
    
    if request.method == 'POST':
        form = UserManagementForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Cập nhật thông tin người dùng {user.full_name} thành công!')
            return redirect('accounts:user_management')
        else:
            messages.error(request, 'Có lỗi xảy ra. Vui lòng kiểm tra lại thông tin.')
    else:
        form = UserManagementForm(instance=user)
    
    # Get user booking statistics if user is customer
    user_completed_bookings = 0
    user_pending_bookings = 0
    if user.is_customer():
        from bookings.models import Booking
        user_completed_bookings = Booking.objects.filter(user=user, status='completed').count()
        user_pending_bookings = Booking.objects.filter(user=user, status='pending').count()
    
    context = {
        'form': form,
        'user_obj': user,
        'user_completed_bookings': user_completed_bookings,
        'user_pending_bookings': user_pending_bookings,
    }
    return render(request, 'accounts/user_edit.html', context)


@require_POST
@user_passes_test(is_manager_or_admin)
def user_toggle_active(request, user_id):
    """Toggle user active status via AJAX"""
    user = get_object_or_404(User, id=user_id)
    
    # Managers cannot deactivate admin users
    if request.user.is_manager() and not request.user.is_admin():
        if user.is_admin():
            return JsonResponse({'success': False, 'message': 'Không có quyền thực hiện.'})
    
    user.is_active = not user.is_active
    user.save()
    
    status = 'kích hoạt' if user.is_active else 'vô hiệu hóa'
    return JsonResponse({
        'success': True,
        'is_active': user.is_active,
        'message': f'Đã {status} tài khoản {user.full_name}.'
    })


@login_required
def dashboard_view(request):
    """Dashboard view - redirect based on user role"""
    if request.user.is_customer():
        return redirect('fields:field_list')
    elif request.user.is_manager() or request.user.is_admin():
        return redirect('accounts:user_management')
    else:
        return redirect('fields:field_list')


@login_required
def notification_list_view(request):
    """Notification center for current user"""
    notifications = request.user.notifications.all().order_by('-created_at')

    # Mark all as read if requested
    if request.GET.get('mark_read') == '1':
        mark_all_notifications_read(request.user)
        messages.success(request, 'Đã đánh dấu tất cả thông báo là đã đọc.')
        return redirect('accounts:notifications')

    context = {
        'notifications': notifications,
    }
    return render(request, 'accounts/notification_list.html', context)

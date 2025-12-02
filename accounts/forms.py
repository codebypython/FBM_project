from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import authenticate
from .models import User, UserProfile


class CustomUserCreationForm(UserCreationForm):
    """Custom user registration form"""
    full_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nhập họ và tên đầy đủ'
        }),
        label='Họ và tên'
    )
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nhập địa chỉ email'
        }),
        label='Email'
    )
    
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nhập tên đăng nhập'
        }),
        label='Tên đăng nhập'
    )
    
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nhập mật khẩu'
        }),
        label='Mật khẩu'
    )
    
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nhập lại mật khẩu'
        }),
        label='Xác nhận mật khẩu'
    )
    
    phone = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nhập số điện thoại (không bắt buộc)'
        }),
        label='Số điện thoại'
    )
    
    class Meta:
        model = User
        fields = ['username', 'full_name', 'email', 'phone', 'password1', 'password2']
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Email này đã được sử dụng.')
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.full_name = self.cleaned_data['full_name']
        user.phone = self.cleaned_data.get('phone', '')
        user.role = 'customer'  # Default role for registration
        
        if commit:
            user.save()
        return user


class CustomAuthenticationForm(AuthenticationForm):
    """Custom login form"""
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Tên đăng nhập'
        }),
        label='Tên đăng nhập'
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mật khẩu'
        }),
        label='Mật khẩu'
    )


class UserProfileForm(forms.ModelForm):
    """User profile edit form"""
    full_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control'
        }),
        label='Họ và tên'
    )
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control'
        }),
        label='Email'
    )
    
    phone = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control'
        }),
        label='Số điện thoại'
    )
    
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3
        }),
        label='Địa chỉ'
    )
    
    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'min': '1900-01-01',
            'max': '2100-12-31',
            'placeholder': 'dd/mm/yyyy'
        }),
        label='Ngày sinh',
        help_text='Chọn hoặc nhập ngày sinh (dd/mm/yyyy)'
    )
    
    class Meta:
        model = UserProfile
        fields = ['avatar', 'bio', 'preferred_field_type']
        widgets = {
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'preferred_field_type': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'avatar': 'Ảnh đại diện',
            'bio': 'Tiểu sử',
            'preferred_field_type': 'Loại sân ưa thích',
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            self.fields['full_name'].initial = self.user.full_name
            self.fields['email'].initial = self.user.email
            self.fields['phone'].initial = self.user.phone
            self.fields['address'].initial = self.user.address
            self.fields['date_of_birth'].initial = self.user.date_of_birth
    
    def clean_date_of_birth(self):
        """Validate date of birth"""
        from datetime import date
        date_of_birth = self.cleaned_data.get('date_of_birth')
        
        if date_of_birth:
            # Check if date is in valid range
            min_date = date(1900, 1, 1)
            max_date = date(2100, 12, 31)
            
            if date_of_birth < min_date or date_of_birth > max_date:
                raise forms.ValidationError('Ngày sinh phải trong khoảng từ 01/01/1900 đến 31/12/2100.')
            
            # Check if date is not in the future (beyond reasonable age)
            today = date.today()
            if date_of_birth > today:
                raise forms.ValidationError('Ngày sinh không thể là ngày trong tương lai.')
        
        return date_of_birth
    
    def save(self, commit=True):
        profile = super().save(commit=False)
        
        if self.user:
            # Update user fields
            self.user.full_name = self.cleaned_data['full_name']
            self.user.email = self.cleaned_data['email']
            self.user.phone = self.cleaned_data['phone']
            self.user.address = self.cleaned_data['address']
            self.user.date_of_birth = self.cleaned_data['date_of_birth']
            
            if commit:
                self.user.save()
        
        if commit:
            profile.save()
        
        return profile


class UserManagementForm(forms.ModelForm):
    """Form for managers to edit user information"""
    class Meta:
        model = User
        fields = ['username', 'full_name', 'email', 'role', 'is_active', 'phone', 'address']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'username': 'Tên đăng nhập',
            'full_name': 'Họ và tên',
            'email': 'Email',
            'role': 'Vai trò',
            'is_active': 'Kích hoạt',
            'phone': 'Số điện thoại',
            'address': 'Địa chỉ',
        }

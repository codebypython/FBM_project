from django import forms
from .models import Field, FieldType, TimeSlot, FieldPricing


class FieldForm(forms.ModelForm):
    """Form for creating and editing fields"""
    
    class Meta:
        model = Field
        fields = ['name', 'field_type', 'location', 'description', 'facilities', 'image', 'layout_image', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'field_type': forms.Select(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'facilities': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'layout_image': forms.FileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'name': 'Tên sân',
            'field_type': 'Loại sân',
            'location': 'Vị trí',
            'description': 'Mô tả',
            'facilities': 'Tiện ích',
            'image': 'Hình ảnh sân',
            'layout_image': 'Sơ đồ vị trí',
            'is_active': 'Hoạt động',
        }

    def clean_name(self):
        """
        Không cho phép tạo hoặc sửa sân với tên đã được sân khác sử dụng
        (không phân biệt hoa/thường, bỏ qua chính bản thân instance hiện tại).
        """
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            return name

        qs = Field.objects.filter(name__iexact=name)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError('Tên sân này đã được sử dụng cho một sân khác. Vui lòng chọn tên khác.')

        return name


class FieldTypeForm(forms.ModelForm):
    """Form for creating and editing field types"""
    
    class Meta:
        model = FieldType
        fields = ['name', 'player_count', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'player_count': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 22}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'name': 'Tên loại sân',
            'player_count': 'Số người chơi',
            'description': 'Mô tả',
        }


class TimeSlotForm(forms.ModelForm):
    """Form for creating and editing time slots"""
    
    class Meta:
        model = TimeSlot
        fields = ['name', 'start_time', 'end_time', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'name': 'Tên khung giờ',
            'start_time': 'Giờ bắt đầu',
            'end_time': 'Giờ kết thúc',
            'is_active': 'Hoạt động',
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        if start_time and end_time:
            if start_time >= end_time:
                raise forms.ValidationError('Giờ kết thúc phải sau giờ bắt đầu.')
        
        return cleaned_data


class FieldPricingForm(forms.ModelForm):
    """Form for creating and editing field pricing"""
    
    class Meta:
        model = FieldPricing
        fields = ['field_type', 'time_slot', 'price', 'weekend_price', 'effective_date', 'is_active']
        widgets = {
            'field_type': forms.Select(attrs={'class': 'form-control'}),
            'time_slot': forms.Select(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': 1000}),
            'weekend_price': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': 1000}),
            'effective_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'field_type': 'Loại sân',
            'time_slot': 'Khung giờ',
            'price': 'Giá thường (VNĐ)',
            'weekend_price': 'Giá cuối tuần (VNĐ)',
            'effective_date': 'Ngày hiệu lực',
            'is_active': 'Hoạt động',
        }


class BulkPricingForm(forms.Form):
    """Form for bulk pricing updates"""
    field_type = forms.ModelChoiceField(
        queryset=FieldType.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Loại sân'
    )
    
    base_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': 1000}),
        label='Giá cơ bản (VNĐ)'
    )
    
    weekend_multiplier = forms.DecimalField(
        max_digits=3,
        decimal_places=2,
        min_value=1,
        initial=1.2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': 0.1}),
        label='Hệ số cuối tuần'
    )
    
    peak_hours = forms.MultipleChoiceField(
        choices=[],
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        label='Khung giờ cao điểm'
    )
    
    peak_multiplier = forms.DecimalField(
        max_digits=3,
        decimal_places=2,
        min_value=1,
        initial=1.5,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': 0.1}),
        label='Hệ số giờ cao điểm'
    )
    
    effective_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='Ngày hiệu lực'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate peak hours choices
        time_slots = TimeSlot.objects.filter(is_active=True).order_by('start_time')
        self.fields['peak_hours'].choices = [
            (slot.id, f"{slot.name} ({slot.start_time.strftime('%H:%M')} - {slot.end_time.strftime('%H:%M')})")
            for slot in time_slots
        ]

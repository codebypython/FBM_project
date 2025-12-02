from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, time, timedelta
from decimal import Decimal

from accounts.models import User, UserProfile
from fields.models import FieldType, Field, TimeSlot, FieldPricing
from bookings.models import Booking

User = get_user_model()


class Command(BaseCommand):
    help = 'Tạo dữ liệu mẫu cho hệ thống quản lý sân bóng mini'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            dest='clear',
            help='Xóa dữ liệu cũ trước khi tạo mới',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Đang xóa dữ liệu cũ...')
            Booking.objects.all().delete()
            FieldPricing.objects.all().delete()
            Field.objects.all().delete()
            TimeSlot.objects.all().delete()
            FieldType.objects.all().delete()
            UserProfile.objects.all().delete()
            User.objects.all().delete()

        self.stdout.write('Bắt đầu tạo dữ liệu mẫu...')

        # Tạo superuser
        self.create_superuser()
        
        # Tạo người dùng mẫu
        self.create_sample_users()
        
        # Tạo loại sân
        self.create_field_types()
        
        # Tạo khung giờ
        self.create_time_slots()
        
        # Tạo sân bóng
        self.create_fields()
        
        # Tạo bảng giá
        self.create_pricing()
        
        # Tạo đơn đặt sân mẫu
        self.create_sample_bookings()

        self.stdout.write(
            self.style.SUCCESS('Tạo dữ liệu mẫu thành công!')
        )

    def create_superuser(self):
        """Tạo superuser admin"""
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser(
                username='admin',
                email='admin@fbmsports.com',
                password='admin123',
                full_name='Administrator',
                role='admin'
            )
            self.stdout.write(f'Tạo superuser: {admin.username}')

    def create_sample_users(self):
        """Tạo người dùng mẫu"""
        users_data = [
            {
                'username': 'manager',
                'email': 'manager@fbmsports.com',
                'password': 'manager123',
                'full_name': 'Nguyễn Văn Quản Lý',
                'role': 'manager',
                'phone': '0123456789'
            },
            {
                'username': 'customer1',
                'email': 'customer1@gmail.com',
                'password': 'customer123',
                'full_name': 'Trần Văn Khách',
                'role': 'customer',
                'phone': '0987654321'
            },
            {
                'username': 'customer2',
                'email': 'customer2@gmail.com',
                'password': 'customer123',
                'full_name': 'Lê Thị Hoa',
                'role': 'customer',
                'phone': '0976543210'
            },
            {
                'username': 'customer3',
                'email': 'customer3@gmail.com',
                'password': 'customer123',
                'full_name': 'Phạm Minh Tuan',
                'role': 'customer',
                'phone': '0965432109'
            }
        ]

        for user_data in users_data:
            if not User.objects.filter(username=user_data['username']).exists():
                user = User.objects.create_user(**user_data)
                self.stdout.write(f'Tạo người dùng: {user.username} ({user.get_role_display()})')

    def create_field_types(self):
        """Tạo loại sân"""
        field_types_data = [
            {
                'name': 'Sân 5',
                'player_count': 5,
                'description': 'Sân bóng đá mini 5 người, phù hợp cho các trận đấu nhỏ'
            },
            {
                'name': 'Sân 7',
                'player_count': 7,
                'description': 'Sân bóng đá 7 người, kích thước trung bình'
            },
            {
                'name': 'Sân 11',
                'player_count': 11,
                'description': 'Sân bóng đá tiêu chuẩn 11 người'
            }
        ]

        for ft_data in field_types_data:
            field_type, created = FieldType.objects.get_or_create(
                name=ft_data['name'],
                defaults=ft_data
            )
            if created:
                self.stdout.write(f'Tạo loại sân: {field_type.name}')

    def create_time_slots(self):
        """Tạo khung giờ"""
        time_slots_data = [
            {'name': 'Sáng sớm', 'start_time': time(6, 0), 'end_time': time(8, 0)},
            {'name': 'Buổi sáng', 'start_time': time(8, 0), 'end_time': time(10, 0)},
            {'name': 'Cuối buổi sáng', 'start_time': time(10, 0), 'end_time': time(12, 0)},
            {'name': 'Buổi trưa', 'start_time': time(12, 0), 'end_time': time(14, 0)},
            {'name': 'Chiều sớm', 'start_time': time(14, 0), 'end_time': time(16, 0)},
            {'name': 'Buổi chiều', 'start_time': time(16, 0), 'end_time': time(18, 0)},
            {'name': 'Chiều muộn', 'start_time': time(18, 0), 'end_time': time(20, 0)},
            {'name': 'Buổi tối', 'start_time': time(20, 0), 'end_time': time(22, 0)},
        ]

        for ts_data in time_slots_data:
            time_slot, created = TimeSlot.objects.get_or_create(
                start_time=ts_data['start_time'],
                end_time=ts_data['end_time'],
                defaults=ts_data
            )
            if created:
                self.stdout.write(f'Tạo khung giờ: {time_slot.name}')

    def create_fields(self):
        """Tạo sân bóng"""
        field_types = {ft.name: ft for ft in FieldType.objects.all()}
        
        fields_data = [
            {
                'name': 'Sân A1',
                'field_type': field_types['Sân 5'],
                'location': 'Khu A - Tầng 1',
                'description': 'Sân bóng mini chất lượng cao với cỏ nhân tạo',
                'facilities': 'Thay đồ, WC, nước uống, ánh sáng LED'
            },
            {
                'name': 'Sân A2',
                'field_type': field_types['Sân 5'],
                'location': 'Khu A - Tầng 1',
                'description': 'Sân bóng mini có mái che',
                'facilities': 'Thay đồ, WC, mái che, quạt mát'
            },
            {
                'name': 'Sân B1',
                'field_type': field_types['Sân 7'],
                'location': 'Khu B - Tầng 1',
                'description': 'Sân bóng 7 người rộng rãi',
                'facilities': 'Thay đồ, WC, ghế ngồi, bảng điện tử'
            },
            {
                'name': 'Sân B2',
                'field_type': field_types['Sân 7'],
                'location': 'Khu B - Tầng 1',
                'description': 'Sân bóng 7 người có điều hòa',
                'facilities': 'Thay đồ, WC, điều hòa, âm thanh'
            },
            {
                'name': 'Sân C1',
                'field_type': field_types['Sân 11'],
                'location': 'Khu C - Sân ngoài',
                'description': 'Sân bóng tiêu chuẩn FIFA',
                'facilities': 'Phòng thay đồ lớn, WC, khán đài'
            }
        ]

        for field_data in fields_data:
            field, created = Field.objects.get_or_create(
                name=field_data['name'],
                defaults=field_data
            )
            if created:
                self.stdout.write(f'Tạo sân bóng: {field.name}')

    def create_pricing(self):
        """Tạo bảng giá"""
        field_types = FieldType.objects.all()
        time_slots = TimeSlot.objects.all()

        # Giá cơ bản theo loại sân
        base_prices = {
            'Sân 5': Decimal('300000'),
            'Sân 7': Decimal('500000'),
            'Sân 11': Decimal('800000'),
        }

        # Hệ số giá theo khung giờ
        time_multipliers = {
            6: 0.8,   # Sáng sớm
            8: 0.9,   # Buổi sáng
            10: 1.0,  # Cuối buổi sáng
            12: 0.8,  # Buổi trưa
            14: 1.0,  # Chiều sớm
            16: 1.2,  # Buổi chiều
            18: 1.5,  # Chiều muộn (prime time)
            20: 1.3,  # Buổi tối
        }

        for field_type in field_types:
            base_price = base_prices.get(field_type.name, Decimal('400000'))
            
            for time_slot in time_slots:
                multiplier = time_multipliers.get(time_slot.start_time.hour, 1.0)
                price = base_price * Decimal(str(multiplier))
                weekend_price = price * Decimal('1.2')  # Cuối tuần +20%

                pricing, created = FieldPricing.objects.get_or_create(
                    field_type=field_type,
                    time_slot=time_slot,
                    defaults={
                        'price': price,
                        'weekend_price': weekend_price,
                        'effective_date': timezone.now().date()
                    }
                )
                if created:
                    self.stdout.write(
                        f'Tạo giá: {field_type.name} - {time_slot.name} - {price:,.0f} VNĐ'
                    )

    def create_sample_bookings(self):
        """Tạo đơn đặt sân mẫu"""
        customers = User.objects.filter(role='customer')
        fields = Field.objects.all()
        time_slots = TimeSlot.objects.all()
        
        if not customers.exists() or not fields.exists():
            return

        # Tạo đơn đặt sân cho 7 ngày tới
        for days_ahead in range(7):
            booking_date = timezone.now().date() + timedelta(days=days_ahead)
            
            # Tạo 2-4 đơn đặt sân mỗi ngày
            import random
            num_bookings = random.randint(2, 4)
            
            for _ in range(num_bookings):
                customer = random.choice(customers)
                field = random.choice(fields)
                time_slot = random.choice(time_slots)
                
                # Kiểm tra xem đã có đơn đặt chưa
                if Booking.objects.filter(
                    field=field,
                    date=booking_date,
                    time_slot=time_slot
                ).exists():
                    continue

                # Lấy giá
                try:
                    pricing = FieldPricing.objects.get(
                        field_type=field.field_type,
                        time_slot=time_slot
                    )
                    total_price = pricing.get_price_for_date(booking_date)
                except FieldPricing.DoesNotExist:
                    total_price = Decimal('400000')

                # Tạo trạng thái ngẫu nhiên
                statuses = ['pending', 'confirmed', 'in_progress', 'completed']
                if booking_date > timezone.now().date():
                    # Đơn đặt tương lai chỉ có thể pending hoặc confirmed
                    status = random.choice(['pending', 'confirmed'])
                elif booking_date == timezone.now().date():
                    # Đơn đặt hôm nay có thể có nhiều trạng thái
                    status = random.choice(statuses)
                else:
                    # Đơn đặt quá khứ chỉ có thể completed
                    status = 'completed'

                booking = Booking.objects.create(
                    user=customer,
                    field=field,
                    time_slot=time_slot,
                    date=booking_date,
                    total_price=total_price,
                    customer_name=customer.full_name,
                    customer_phone=customer.phone or '0123456789',
                    status=status,
                    payment_status='paid' if status == 'completed' else 'pending',
                    note=f'Đơn đặt sân mẫu cho {customer.full_name}'
                )
                
                self.stdout.write(
                    f'Tạo đơn đặt sân: #{booking.id} - {field.name} - {booking_date} - {status}'
                )

        self.stdout.write(f'Tạo tổng cộng {Booking.objects.count()} đơn đặt sân mẫu')

from django.db import migrations
from django.utils import timezone


def create_abc_fields(apps, schema_editor):
    Field = apps.get_model('fields', 'Field')
    FieldType = apps.get_model('fields', 'FieldType')

    now = timezone.now()

    # Vô hiệu hóa sân test nếu tồn tại
    Field.objects.filter(name='Sân Test').update(is_active=False, updated_at=now)

    # Lấy loại sân
    try:
        san5 = FieldType.objects.get(name='Sân 5')
    except FieldType.DoesNotExist:
        san5 = None
    try:
        san7 = FieldType.objects.get(name='Sân 7')
    except FieldType.DoesNotExist:
        san7 = None

    fields_to_create = []

    # Sân 5 người (tổng 10 sân)
    if san5:
        fields_5 = [
            # Khu A (đã có A1, A2 trong DB hiện tại)
            ('Sân 5 A3', 'Khu A', 'Sân 5 người, mặt cỏ nhân tạo, gần cổng vào khu A.'),
            ('Sân 5 A4', 'Khu A', 'Sân 5 người, nằm giữa dãy sân khu A, phù hợp thi đấu giải nhỏ.'),
            # Khu B
            ('Sân 5 B1', 'Khu B', 'Sân 5 người trung tâm khu B, thuận tiện di chuyển.'),
            ('Sân 5 B2', 'Khu B', 'Sân 5 người cạnh khu vực khán giả, phù hợp giao hữu.'),
            ('Sân 5 B3', 'Khu B', 'Sân 5 người phía cuối khu B, yên tĩnh, ít ồn.'),
            # Khu C
            ('Sân 5 C1', 'Khu C', 'Sân 5 người đầu dãy khu C, phù hợp tập luyện.'),
            ('Sân 5 C2', 'Khu C', 'Sân 5 người giữa dãy khu C, mặt sân đẹp.'),
            ('Sân 5 C3', 'Khu C', 'Sân 5 người sát hàng rào khuôn viên, yên tĩnh.'),
        ]
        for name, location, desc in fields_5:
            if not Field.objects.filter(name=name).exists():
                fields_to_create.append(
                    Field(
                        name=name,
                        location=location,
                        description=desc,
                        facilities='Đèn chiếu sáng, phòng thay đồ, WC, nước uống.',
                        image='',
                        layout_image='',
                        is_active=True,
                        created_at=now,
                        updated_at=now,
                        field_type=san5,
                    )
                )

    # Sân 7 người (tổng 5 sân)
    if san7:
        fields_7 = [
            # Khu A
            ('Sân 7 A1', 'Khu A', 'Sân 7 người gần cổng, thích hợp tổ chức giải phong trào.'),
            ('Sân 7 A2', 'Khu A', 'Sân 7 người nằm phía trong, mặt sân chất lượng cao.'),
            # Khu C
            ('Sân 7 C1', 'Khu C', 'Sân 7 người cuối khuôn viên, yên tĩnh, phù hợp thi đấu cường độ cao.'),
        ]
        for name, location, desc in fields_7:
            if not Field.objects.filter(name=name).exists():
                fields_to_create.append(
                    Field(
                        name=name,
                        location=location,
                        description=desc,
                        facilities='Đèn chiếu sáng, phòng thay đồ, WC, nước uống, khu khán giả nhỏ.',
                        image='',
                        layout_image='',
                        is_active=True,
                        created_at=now,
                        updated_at=now,
                        field_type=san7,
                    )
                )

    if fields_to_create:
        Field.objects.bulk_create(fields_to_create)


def remove_abc_fields(apps, schema_editor):
    Field = apps.get_model('fields', 'Field')

    names_to_delete = [
        'Sân 5 A3', 'Sân 5 A4',
        'Sân 5 B1', 'Sân 5 B2', 'Sân 5 B3',
        'Sân 5 C1', 'Sân 5 C2', 'Sân 5 C3',
        'Sân 7 A1', 'Sân 7 A2', 'Sân 7 C1',
    ]
    Field.objects.filter(name__in=names_to_delete).delete()

    # Bật lại sân test nếu tồn tại
    Field = apps.get_model('fields', 'Field')
    Field.objects.filter(name='Sân Test').update(is_active=True)


class Migration(migrations.Migration):

    dependencies = [
        ('fields', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_abc_fields, remove_abc_fields),
    ]



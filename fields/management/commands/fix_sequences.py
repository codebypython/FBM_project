"""
Management command to fix PostgreSQL sequence issues.

This command synchronizes PostgreSQL sequences with the actual max ID values
in the database tables. This is useful when data is imported or deleted manually,
causing sequence values to be out of sync.

Usage:
    python manage.py fix_sequences
    python manage.py fix_sequences --app fields
    python manage.py fix_sequences --model FieldPricing
"""

from django.core.management.base import BaseCommand
from django.db import connection
from django.apps import apps
from django.db.models import Max


class Command(BaseCommand):
    help = 'Fix PostgreSQL sequences for all models or specific app/model'

    def add_arguments(self, parser):
        parser.add_argument(
            '--app',
            type=str,
            help='Fix sequences for a specific app (e.g., fields)',
        )
        parser.add_argument(
            '--model',
            type=str,
            help='Fix sequence for a specific model (e.g., FieldPricing)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually fixing sequences',
        )

    def handle(self, *args, **options):
        app_name = options.get('app')
        model_name = options.get('model')
        dry_run = options.get('dry_run', False)

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made\n'))

        # Get models to process
        models_to_fix = []
        
        if model_name:
            # Fix specific model
            if app_name:
                try:
                    model = apps.get_model(app_name, model_name)
                    models_to_fix = [model]
                except LookupError:
                    self.stdout.write(self.style.ERROR(f'Model {app_name}.{model_name} not found'))
                    return
            else:
                # Search all apps
                found = False
                for app_config in apps.get_app_configs():
                    try:
                        model = apps.get_model(app_config.label, model_name)
                        models_to_fix.append(model)
                        found = True
                    except LookupError:
                        continue
                if not found:
                    self.stdout.write(self.style.ERROR(f'Model {model_name} not found in any app'))
                    return
        elif app_name:
            # Fix all models in specific app
            try:
                app_config = apps.get_app_config(app_name)
                models_to_fix = list(app_config.get_models())
            except LookupError:
                self.stdout.write(self.style.ERROR(f'App {app_name} not found'))
                return
        else:
            # Fix all models in all apps
            for app_config in apps.get_app_configs():
                models_to_fix.extend(app_config.get_models())

        if not models_to_fix:
            self.stdout.write(self.style.WARNING('No models found to fix'))
            return

        fixed_count = 0
        skipped_count = 0

        with connection.cursor() as cursor:
            for model in models_to_fix:
                # Skip if model doesn't have an 'id' field or uses custom primary key
                if not hasattr(model, '_meta'):
                    continue
                
                pk_field = model._meta.pk
                if not hasattr(pk_field, 'column') or pk_field.column != 'id':
                    skipped_count += 1
                    continue

                table_name = model._meta.db_table
                sequence_name = f"{table_name}_id_seq"

                # Check if sequence exists
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_class 
                        WHERE relname = %s AND relkind = 'S'
                    )
                """, [sequence_name])

                if not cursor.fetchone()[0]:
                    self.stdout.write(
                        self.style.WARNING(f'  ⚠ Sequence {sequence_name} does not exist, skipping')
                    )
                    skipped_count += 1
                    continue

                # Get max ID from table
                try:
                    max_id_result = model.objects.aggregate(Max('id'))
                    max_id = max_id_result['id__max']
                    
                    if max_id is None:
                        max_id = 0
                        self.stdout.write(
                            self.style.WARNING(f'  ⚠ {model.__name__}: Table is empty, setting sequence to 1')
                        )
                        new_seq_value = 1
                    else:
                        new_seq_value = max_id + 1
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'  ✗ {model.__name__}: Error getting max ID - {str(e)}')
                    )
                    skipped_count += 1
                    continue

                # Get current sequence value
                cursor.execute(f"SELECT last_value, is_called FROM {sequence_name}")
                current_value, is_called = cursor.fetchone()

                if current_value < new_seq_value or (current_value == new_seq_value and is_called):
                    if not dry_run:
                        # Fix sequence
                        cursor.execute(f"SELECT setval('{sequence_name}', {new_seq_value}, false)")
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  ✓ {model.__name__}: Fixed sequence from {current_value} to {new_seq_value}'
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f'  → {model.__name__}: Would fix sequence from {current_value} to {new_seq_value}'
                            )
                        )
                    fixed_count += 1
                else:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  ✓ {model.__name__}: Sequence is already correct ({current_value})'
                        )
                    )

        self.stdout.write('\n' + '='*60)
        if dry_run:
            self.stdout.write(self.style.WARNING(f'DRY RUN: Would fix {fixed_count} sequences, skipped {skipped_count}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Fixed {fixed_count} sequences, skipped {skipped_count}'))
        self.stdout.write('='*60)


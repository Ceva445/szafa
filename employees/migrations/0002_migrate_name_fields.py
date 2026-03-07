# employees/migrations/0002_rename_fields.py
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('employees', '0001_initial'),
    ]

    operations = [
        # Просто перейменовуємо поля
        migrations.RenameField(
            model_name='employee',
            old_name='first_name',
            new_name='_first_name',
        ),
        migrations.RenameField(
            model_name='employee',
            old_name='last_name',
            new_name='_last_name',
        ),
        
        # Оновлюємо Meta.ordering
        migrations.AlterModelOptions(
            name='employee',
            options={'ordering': ['_last_name', '_first_name']},
        ),
    ]
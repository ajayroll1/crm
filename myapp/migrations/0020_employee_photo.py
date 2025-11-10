from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0019_paymenttransaction_employee_snapshots'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='photo',
            field=models.ImageField(blank=True, null=True, upload_to='uploads/employees/photos/', verbose_name='Profile Photo'),
        ),
    ]


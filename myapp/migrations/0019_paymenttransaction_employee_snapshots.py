from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0018_paymenttransaction'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymenttransaction',
            name='employee_department',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Department Snapshot'),
        ),
        migrations.AddField(
            model_name='paymenttransaction',
            name='employee_name',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Employee Name Snapshot'),
        ),
    ]


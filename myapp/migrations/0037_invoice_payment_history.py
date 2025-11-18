from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0036_invoice_amount_received'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='payment_history',
            field=models.JSONField(blank=True, default=list, help_text='List of partial payments with amount and date'),
        ),
    ]


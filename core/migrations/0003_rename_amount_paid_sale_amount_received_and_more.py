# Generated by Django 5.2 on 2025-04-30 08:58

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_payment_sale_alter_produce_type'),
    ]

    operations = [
        migrations.RenameField(
            model_name='sale',
            old_name='amount_paid',
            new_name='amount_received',
        ),
        migrations.RemoveField(
            model_name='sale',
            name='total_amount',
        ),
    ]

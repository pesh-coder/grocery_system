# Generated by Django 5.2 on 2025-05-02 09:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_alter_sale_amount_received'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sale',
            name='change',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=15),
        ),
    ]

# Generated by Django 5.2.2 on 2025-07-03 05:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Tienda', '0004_alter_producto_codigo_barras'),
    ]

    operations = [
        migrations.AddField(
            model_name='proveedor',
            name='verify_digit',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='proveedor',
            name='rut',
            field=models.PositiveIntegerField(unique=True),
        ),
    ]

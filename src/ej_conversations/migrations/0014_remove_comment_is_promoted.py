# Generated by Django 2.1.7 on 2019-03-18 03:03

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("ej_conversations", "0013_auto_20190310_2215")]

    operations = [migrations.RemoveField(model_name="comment", name="is_promoted")]

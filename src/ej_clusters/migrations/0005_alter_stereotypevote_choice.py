# Generated by Django 4.1.13 on 2024-10-01 14:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ej_clusters", "0004_alter_clusterization_cluster_status_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="stereotypevote",
            name="choice",
            field=models.IntegerField(
                choices=[(0, "Skip"), (1, "Agree"), (-1, "Disagree")]
            ),
        ),
    ]

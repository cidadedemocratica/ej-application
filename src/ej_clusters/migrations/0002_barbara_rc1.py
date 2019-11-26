# Generated by Django 2.2.2 on 2019-07-02 16:34

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("ej_conversations", "0002_barbara_rc1"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("ej_clusters", "0001_ada_lovelace_v1"),
    ]

    operations = [
        migrations.RemoveField(model_name="clusterization", name="unprocessed_comments"),
        migrations.RemoveField(model_name="clusterization", name="unprocessed_votes"),
        migrations.AddField(
            model_name="clusterization",
            name="pending_comments",
            field=models.ManyToManyField(
                blank=True,
                editable=False,
                related_name="pending_in_clusterizations",
                to="ej_conversations.Comment",
            ),
        ),
        migrations.AddField(
            model_name="clusterization",
            name="pending_votes",
            field=models.ManyToManyField(
                blank=True,
                editable=False,
                related_name="pending_in_clusterizations",
                to="ej_conversations.Vote",
            ),
        ),
        migrations.AlterField(
            model_name="stereotype",
            name="description",
            field=models.TextField(
                blank=True,
                help_text="Specify a background history, or give hints about the profile this persona wants to capture. This information is optional and is not made public.",
                verbose_name="Description",
            ),
        ),
        migrations.AlterField(
            model_name="stereotype",
            name="name",
            field=models.CharField(
                help_text="Public identification of persona.", max_length=64, verbose_name="Name"
            ),
        ),
        migrations.AlterField(
            model_name="stereotype",
            name="owner",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="stereotypes",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterUniqueTogether(name="stereotype", unique_together={("name", "owner")}),
        migrations.AlterUniqueTogether(name="stereotypevote", unique_together={("author", "comment")}),
        migrations.RemoveField(model_name="stereotype", name="conversation"),
    ]

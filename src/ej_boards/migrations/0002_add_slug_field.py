# Generated by Django 2.0.8 on 2018-10-11 01:43

from django.db import migrations, models
import ej_boards.validators


class Migration(migrations.Migration):

    dependencies = [("ej_boards", "0001_first_migration")]

    operations = [
        migrations.AlterField(
            model_name="board",
            name="slug",
            field=models.SlugField(
                unique=True, validators=[ej_boards.validators.validate_board_slug], verbose_name="Slug"
            ),
        )
    ]

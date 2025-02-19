# Generated by Django 3.2 on 2023-08-11 22:53

import ckeditor.fields
from django.db import migrations, models
import django.db.models.deletion
from ej_conversations.validators import validate_file_size


class Migration(migrations.Migration):

    dependencies = [
        ('ej_conversations', '0019_alter_vote_channel'),
        ('ej_integrations', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='OpinionComponent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('background_image', models.ImageField(upload_to='opinion_component/background/', validators=[validate_file_size])),
                ('logo_image', models.ImageField(upload_to='opinion_component/logo/', validators=[validate_file_size])),
                ('final_voting_message', ckeditor.fields.RichTextField()),
                ('conversation', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='ej_conversations.conversation')),
            ],
        ),
    ]

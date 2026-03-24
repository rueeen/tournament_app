from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('matches', '0002_matchnotification'),
    ]

    operations = [
        migrations.AddField(
            model_name='matchnotification',
            name='action_label',
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name='matchnotification',
            name='action_url',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='matchnotification',
            name='metadata',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='matchnotification',
            name='read_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='matchnotification',
            name='title',
            field=models.CharField(default='Notificación', max_length=120),
        ),
        migrations.AlterField(
            model_name='matchnotification',
            name='message',
            field=models.TextField(),
        ),
        migrations.AddIndex(
            model_name='matchnotification',
            index=models.Index(fields=['recipient', 'is_read', '-created_at'], name='matches_mat_recipie_ff9374_idx'),
        ),
        migrations.AddIndex(
            model_name='matchnotification',
            index=models.Index(fields=['recipient', '-created_at'], name='matches_mat_recipie_2b7f84_idx'),
        ),
        migrations.AddIndex(
            model_name='matchnotification',
            index=models.Index(fields=['created_at'], name='matches_mat_created_80ee14_idx'),
        ),
    ]

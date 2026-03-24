from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('matches', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='MatchNotification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notification_type', models.CharField(choices=[('match_created', 'Partida creada'), ('invitation_accepted', 'Invitación aceptada'), ('invitation_rejected', 'Invitación rechazada'), ('result_proposed', 'Resultado propuesto'), ('result_accepted', 'Resultado aceptado'), ('result_rejected', 'Resultado rechazado'), ('match_finalized', 'Partida finalizada')], max_length=32)),
                ('message', models.CharField(max_length=220)),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('actor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='triggered_match_notifications', to=settings.AUTH_USER_MODEL)),
                ('match', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='matches.match')),
                ('recipient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='match_notifications', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]

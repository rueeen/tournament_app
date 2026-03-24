from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('decks', '0002_alter_deck_losses_alter_deck_total_matches_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='deck',
            name='cover_image_url',
            field=models.URLField(blank=True),
        ),
    ]

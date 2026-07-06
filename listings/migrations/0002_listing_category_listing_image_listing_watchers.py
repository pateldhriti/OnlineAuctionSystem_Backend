from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('listings', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='listing',
            name='category',
            field=models.CharField(
                choices=[
                    ('electronics', 'Electronics'),
                    ('fashion', 'Fashion'),
                    ('home', 'Home'),
                    ('books', 'Books'),
                    ('sports', 'Sports'),
                    ('toys', 'Toys'),
                    ('vehicles', 'Vehicles'),
                    ('other', 'Other'),
                ],
                default='other',
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name='listing',
            name='image',
            field=models.ImageField(blank=True, upload_to='listing_images/'),
        ),
        migrations.AddField(
            model_name='listing',
            name='watchers',
            field=models.ManyToManyField(
                blank=True,
                related_name='watchlist',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0009_populate_unique_slugs'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='slug',
            field=models.SlugField(blank=True, max_length=255, unique=True),
        ),
    ]

from django.db import migrations
from django.utils.text import slugify


def generate_unique_slug(apps, schema_editor):
    Product = apps.get_model('store', 'Product')
    existing = set()
    for product in Product.objects.all():
        base = slugify(product.name)[:200]
        slug = base
        i = 1
        while slug in existing or Product.objects.filter(slug=slug).exclude(pk=product.pk).exists():
            slug = f"{base}-{i}"
            i += 1
        product.slug = slug
        product.save()
        existing.add(slug)


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0008_product_created_product_description_and_more'),
    ]

    operations = [
        migrations.RunPython(generate_unique_slug, reverse_code=migrations.RunPython.noop),
    ]

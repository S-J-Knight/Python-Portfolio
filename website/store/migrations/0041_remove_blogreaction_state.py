# Manual migration to remove BlogReaction from Django's migration state
from django.db import migrations


def drop_blogreaction_safely(apps, schema_editor):
    """Drop BlogReaction table if it exists (for test databases)"""
    schema_editor.execute('DROP TABLE IF EXISTS store_blogreaction;')


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0040_customer_custom_subscription_price_and_more'),
    ]

    operations = [
        # First, drop the table safely if it exists
        migrations.RunPython(drop_blogreaction_safely, reverse_code=migrations.RunPython.noop),
        # Then remove from Django's state tracking without trying to drop the table again
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name='BlogReaction'),
            ],
            database_operations=[
                # No database operations - table already dropped above
            ]
        ),
    ]

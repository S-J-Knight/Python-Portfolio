import os
import django
import pytest
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website.settings')

def pytest_configure():
    if not settings.configured:
        django.setup()

@pytest.fixture(scope="session")
def setup_database():
    # Setup code here
    yield
    # Teardown code here

@pytest.fixture
def sample_data():
    return {"key": "value"}
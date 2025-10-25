"""
WSGI config for KnightCycle website on IONOS hosting.

This file is used by Passenger (IONOS's Python app server) to serve the Django application.
"""

import sys
import os

# === IMPORTANT: Update this path to your actual website directory on IONOS ===
# Example: '/home/customer/www/knightcycle.co.uk/public_html/website'
project_home = '/path/to/your/website'  # TODO: Update this!

# Add your project directory to the sys.path
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set environment variable for Django settings
os.environ['DJANGO_SETTINGS_MODULE'] = 'website.settings'

# Load environment variables from .env if it exists
# Note: On IONOS, you should set environment variables in the hosting panel instead
from pathlib import Path
env_path = Path(project_home) / '.env'
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)

# Import Django WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

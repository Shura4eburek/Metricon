"""WSGI config for Metricon project."""
import os

from django.core.wsgi import get_wsgi_application

# Use production settings on Railway (DATABASE_URL is set), local otherwise
if os.environ.get('DATABASE_URL') or os.environ.get('RAILWAY_ENVIRONMENT'):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'metricon.settings.production')
else:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'metricon.settings.local')

application = get_wsgi_application()

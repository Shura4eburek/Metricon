web: python manage.py migrate && gunicorn metricon.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 60

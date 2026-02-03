web: python deploy.py && gunicorn trimed_backend.wsgi:application --bind 0.0.0.0:$PORT
release: python force_migrate.py
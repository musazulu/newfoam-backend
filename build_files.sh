#!/bin/bash

# Install dependencies from the clean requirements file
pip install -r requirements-prod.txt

# Collect static files
python manage.py collectstatic --noinput

# Run database migrations
python manage.py migrate --noinput

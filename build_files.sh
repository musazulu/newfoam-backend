#!/bin/bash
# Build script — also installs deps as a safety net (builder auto-installs from requirements.txt too)
pip install -r requirements.txt

# Collect static files for Whitenoise
python manage.py collectstatic --noinput

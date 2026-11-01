#!/bin/bash
# Build script — Vercel's @vercel/python builder auto-installs from requirements.txt via uv.
# This script runs collectstatic for Whitenoise static file serving.
python manage.py collectstatic --noinput

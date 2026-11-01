"""
WSGI config for backend project.
"""

import os
import sys
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

# Attempt to load Django — capture any startup error and serve it as plain text
# so Vercel logs and browser show the exact traceback instead of a generic 500
_startup_error = None
_application = None

try:
    from django.core.wsgi import get_wsgi_application
    _application = get_wsgi_application()
except Exception:
    _startup_error = traceback.format_exc()


def application(environ, start_response):
    if _startup_error:
        error_body = (
            "DJANGO STARTUP FAILED\n\n" + _startup_error
        ).encode('utf-8')
        start_response('500 Internal Server Error', [
            ('Content-Type', 'text/plain; charset=utf-8'),
            ('Content-Length', str(len(error_body))),
        ])
        return [error_body]
    return _application(environ, start_response)

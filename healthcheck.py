"""Script de HEALTHCHECK Docker — interroge /api/health et sort en erreur si indisponible."""

import os
import sys
import urllib.error
import urllib.request

port = os.environ.get("PORT", "8000")

try:
    urllib.request.urlopen(f"http://localhost:{port}/api/health", timeout=3)
except (urllib.error.URLError, OSError):
    sys.exit(1)

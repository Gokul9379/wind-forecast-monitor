"""Vercel serverless entry point: Vercel looks for an ASGI `app` object here."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.main import app  # noqa: E402,F401

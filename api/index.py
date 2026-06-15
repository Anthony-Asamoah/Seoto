"""Vercel serverless entrypoint for the Django WSGI app."""
from seoto.wsgi import application

# Vercel's Python runtime looks for a module-level `app` callable.
app = application

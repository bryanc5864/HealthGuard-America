"""
Vercel serverless function entry point for HealthGuard Flask app.
"""
import sys
from pathlib import Path

# Add project paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / 'frontend'))

# Set environment to production
import os
os.environ['FLASK_ENV'] = 'production'
os.environ['VERCEL'] = '1'

# Import Flask app
from frontend.app import app

# Vercel expects 'app' to be the WSGI application
app = app

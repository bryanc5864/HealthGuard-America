"""
Shared Flask extension instances.

Kept in their own module so both app.py and the blueprint modules can import
them without creating a circular import with app.py.
"""
from flask_wtf.csrf import CSRFProtect

# CSRF protection for state-changing form POSTs (e.g. gov login).
# Initialized against the app in app.py via csrf.init_app(app).
csrf = CSRFProtect()

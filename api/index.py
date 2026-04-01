"""
Vercel serverless function entry point for HealthGuard Flask app.
Runs with minimal dependencies (Flask only) - no pandas/numpy/pyarrow.
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

# Stub out heavy libraries before importing app
import types

# Create lightweight pandas stub
pd = types.ModuleType('pandas')
pd.DataFrame = type('DataFrame', (), {
    '__init__': lambda self, *a, **kw: None,
    '__len__': lambda self: 0,
    '__bool__': lambda self: False,
    'empty': True,
    'columns': [],
    'head': lambda self, *a: self,
    'to_dict': lambda self, *a: [],
    'dropna': lambda self, **kw: self,
    'fillna': lambda self, *a, **kw: self,
    'sort_values': lambda self, *a, **kw: self,
    'astype': lambda self, *a, **kw: self,
    'value_counts': lambda self: self,
    'unique': lambda self: [],
    'mean': lambda self: 0,
    'sum': lambda self: 0,
    'get': lambda self, *a, **kw: pd.Series(),
    '__getitem__': lambda self, *a: self,
    '__setitem__': lambda self, *a: None,
})
pd.Series = type('Series', (), {
    '__init__': lambda self, *a, **kw: None,
    'dropna': lambda self: self,
    'mean': lambda self: 0,
    'sum': lambda self: 0,
    'unique': lambda self: [],
    'fillna': lambda self, *a, **kw: self,
    'str': property(lambda self: self),
    'lower': lambda self: self,
    'contains': lambda self, *a, **kw: self,
    'astype': lambda self, *a, **kw: self,
    'value_counts': lambda self: {},
    '__len__': lambda self: 0,
})
pd.read_csv = lambda *a, **kw: pd.DataFrame()
pd.read_parquet = lambda *a, **kw: pd.DataFrame()
pd.read_excel = lambda *a, **kw: pd.DataFrame()
pd.to_numeric = lambda *a, **kw: pd.Series()
pd.isna = lambda x: x is None
sys.modules['pandas'] = pd

# Numpy stub
np = types.ModuleType('numpy')
np.mean = lambda x, **kw: 0
np.median = lambda x, **kw: 0
np.std = lambda x, **kw: 0
np.min = lambda x, **kw: 0
np.max = lambda x, **kw: 0
sys.modules['numpy'] = np

# Pyarrow stub
pa = types.ModuleType('pyarrow')
pa.parquet = types.ModuleType('pyarrow.parquet')
sys.modules['pyarrow'] = pa
sys.modules['pyarrow.parquet'] = pa.parquet

# Ensure frontend dir is on path BEFORE importing app
# On Vercel, app.py's relative path insert may not work
FRONTEND_DIR = str(PROJECT_ROOT / 'frontend')
if FRONTEND_DIR not in sys.path:
    sys.path.insert(0, FRONTEND_DIR)

# Import Flask app
from frontend.app import app

# Vercel expects 'app' to be the WSGI application
app = app

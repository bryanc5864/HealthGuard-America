"""
Vercel serverless entry point.
Stubs heavy deps, loads Flask app from frontend/.
"""
import sys
import os
import types
from pathlib import Path

PROJECT_ROOT = str(Path(__file__).parent.parent)
FRONTEND_DIR = os.path.join(PROJECT_ROOT, 'frontend')

sys.path.insert(0, FRONTEND_DIR)
sys.path.insert(0, PROJECT_ROOT)

os.environ['FLASK_ENV'] = 'production'
os.environ['VERCEL'] = '1'


# === Comprehensive stubs for all heavy libraries ===

def _make_stub(name):
    mod = types.ModuleType(name)
    mod.__path__ = []
    sys.modules[name] = mod
    return mod


class FakeDF:
    """Comprehensive pandas DataFrame/Series stub that won't crash."""
    empty = True
    columns = []
    values = []
    index = []
    shape = (0, 0)
    dtypes = {}
    name = None
    str = None

    def __init__(self, *a, **kw):
        self.str = self

    # Comparison / boolean
    def __len__(self): return 0
    def __bool__(self): return False
    def __iter__(self): return iter([])
    def __contains__(self, x): return False
    def __eq__(self, other): return self
    def __ne__(self, other): return self
    def __gt__(self, other): return self
    def __lt__(self, other): return self
    def __ge__(self, other): return self
    def __le__(self, other): return self
    def __and__(self, other): return self
    def __or__(self, other): return self
    def __invert__(self): return self
    def __getattr__(self, name):
        if name.startswith('__') and name.endswith('__'):
            raise AttributeError(name)
        return self
    def __getitem__(self, *a): return self
    def __setitem__(self, *a): pass
    def __call__(self, *a, **kw): return self

    # Data access
    def head(self, *a): return self
    def tail(self, *a): return self
    def to_dict(self, *a, **kw): return []
    def to_list(self): return []
    def tolist(self): return []
    def to_records(self, *a, **kw): return []
    def items(self): return iter([])
    def iterrows(self): return iter([])
    def iteritems(self): return iter([])
    @property
    def iloc(self): return self
    @property
    def loc(self): return self

    # Filtering
    def dropna(self, **kw): return self
    def fillna(self, *a, **kw): return self
    def where(self, *a, **kw): return self
    def mask(self, *a, **kw): return self
    def isin(self, *a): return self
    def notna(self): return self
    def isna(self): return self
    def between(self, *a): return self
    def duplicated(self, *a, **kw): return self
    def drop_duplicates(self, *a, **kw): return self

    # Sorting/transforming
    def sort_values(self, *a, **kw): return self
    def sort_index(self, *a, **kw): return self
    def astype(self, *a, **kw): return self
    def apply(self, *a, **kw): return self
    def map(self, *a, **kw): return self
    def replace(self, *a, **kw): return self
    def rename(self, *a, **kw): return self
    def reset_index(self, *a, **kw): return self
    def set_index(self, *a, **kw): return self
    def copy(self): return self
    def sample(self, *a, **kw): return self
    def groupby(self, *a, **kw): return self
    def agg(self, *a, **kw): return self
    def merge(self, *a, **kw): return self
    def concat(self, *a, **kw): return self
    def assign(self, **kw): return self

    # Aggregation
    def value_counts(self): return {}
    def unique(self): return []
    def nunique(self): return 0
    def count(self): return 0
    def mean(self): return 0
    def median(self): return 0
    def sum(self): return 0
    def min(self): return 0
    def max(self): return 0
    def std(self): return 0
    def var(self): return 0
    def describe(self): return self
    def get(self, *a, **kw): return self

    # String methods (for .str accessor)
    def lower(self): return self
    def upper(self): return self
    def contains(self, *a, **kw): return self
    def strip(self): return self
    def replace(self, *a, **kw): return self
    def startswith(self, *a): return self
    def endswith(self, *a): return self


# Pandas stub
pd = _make_stub('pandas')
pd.DataFrame = FakeDF
pd.Series = FakeDF
pd.read_csv = lambda *a, **kw: FakeDF()
pd.read_parquet = lambda *a, **kw: FakeDF()
pd.read_excel = lambda *a, **kw: FakeDF()
pd.to_numeric = lambda *a, **kw: FakeDF()
pd.isna = lambda x: x is None
pd.concat = lambda *a, **kw: FakeDF()

# Numpy stub
np = _make_stub('numpy')
np.mean = np.median = np.std = np.min = np.max = lambda x, **kw: 0
np.ndarray = type('ndarray', (), {})
np.array = lambda *a, **kw: []
np.float32 = np.float64 = np.int32 = np.int64 = float

# Pyarrow
_make_stub('pyarrow')
_make_stub('pyarrow.parquet')

# ML ecosystem stubs
for name in ['torch', 'torch.nn', 'torch.nn.functional', 'torch.optim',
             'torch.utils', 'torch.utils.data', 'sklearn', 'sklearn.preprocessing',
             'sklearn.utils', 'sklearn.utils._param_validation', 'tensorflow',
             'transformers', 'joblib', 'scipy', 'scipy.sparse']:
    _make_stub(name)

# ML package stubs
for name in ['ml', 'ml.chroniccare', 'ml.chroniccare.inference', 'ml.chroniccare.model',
             'ml.nova_classifier', 'ml.nova_classifier.inference',
             'ml.additive_scorer', 'ml.additive_scorer.inference',
             'ml.procedure_encoder', 'ml.procedure_encoder.inference']:
    _make_stub(name)

# Dummy ML service classes
sys.modules['ml.chroniccare.inference'].ChronicCareMLService = type(
    'ChronicCareMLService', (), {'is_loaded': False})
sys.modules['ml.chroniccare.inference'].get_chroniccare_service = (
    lambda: sys.modules['ml.chroniccare.inference'].ChronicCareMLService())
sys.modules['ml.nova_classifier.inference'].NovaClassificationService = type(
    'NovaClassificationService', (), {'load': classmethod(lambda cls: None)})
sys.modules['ml.additive_scorer.inference'].AdditiveRiskService = type(
    'AdditiveRiskService', (), {'load': classmethod(lambda cls: None)})
sys.modules['ml.procedure_encoder.inference'].ProcedureMatchingService = type(
    'ProcedureMatchingService', (), {'load': classmethod(lambda cls: None)})


# === Load Flask app ===
from app import app

# Add error handler for Vercel - catch any route errors gracefully
@app.errorhandler(500)
def vercel_error_handler(e):
    from flask import render_template
    try:
        return render_template('landing.html',
                               modules=app.config.get('MODULES', {})), 500
    except Exception:
        return f"<h1>HealthGuard America</h1><p>This feature requires the full server. <a href='/'>Home</a></p>", 500

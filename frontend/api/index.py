"""
Vercel serverless entry point.
Stubs heavy libraries, then loads app.py via runpy to avoid package-context issues.
"""
import sys
import os
import types
from pathlib import Path

# This file is at frontend/api/index.py
FRONTEND_DIR = str(Path(__file__).parent.parent)
PROJECT_ROOT = str(Path(__file__).parent.parent.parent)

sys.path.insert(0, FRONTEND_DIR)
sys.path.insert(0, PROJECT_ROOT)

os.environ['FLASK_ENV'] = 'production'
os.environ['VERCEL'] = '1'


# === Stub ALL heavy libraries that aren't installed on Vercel ===

def _make_stub(name, extras=None):
    """Create a stub module and register it in sys.modules."""
    mod = types.ModuleType(name)
    mod.__path__ = []  # Make it a package so sub-imports don't fail
    if extras:
        for k, v in extras.items():
            setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


# Pandas stub
pd = _make_stub('pandas')


class FakeDF:
    empty = True
    columns = []

    def __init__(self, *a, **kw): pass
    def __len__(self): return 0
    def __bool__(self): return False
    def head(self, *a): return self
    def to_dict(self, *a): return []
    def dropna(self, **kw): return self
    def fillna(self, *a, **kw): return self
    def sort_values(self, *a, **kw): return self
    def astype(self, *a, **kw): return self
    def value_counts(self): return self
    def unique(self): return []
    def mean(self): return 0
    def sum(self): return 0
    def get(self, *a, **kw): return FakeDF()
    def __getitem__(self, *a): return self
    def __setitem__(self, *a): pass
    def copy(self): return self


pd.DataFrame = FakeDF
pd.Series = FakeDF
pd.read_csv = lambda *a, **kw: FakeDF()
pd.read_parquet = lambda *a, **kw: FakeDF()
pd.read_excel = lambda *a, **kw: FakeDF()
pd.to_numeric = lambda *a, **kw: FakeDF()
pd.isna = lambda x: x is None

# Numpy stub
np = _make_stub('numpy')
np.mean = np.median = np.std = np.min = np.max = lambda x, **kw: 0
np.ndarray = type('ndarray', (), {})
np.array = lambda *a, **kw: []
np.float32 = np.float64 = np.int32 = np.int64 = float

# Pyarrow stub
_make_stub('pyarrow')
_make_stub('pyarrow.parquet')

# Torch + sklearn + tensorflow stubs (used by ML modules)
_make_stub('torch')
_make_stub('torch.nn')
_make_stub('torch.nn.functional')
_make_stub('torch.optim')
_make_stub('torch.utils')
_make_stub('torch.utils.data')
_make_stub('sklearn')
_make_stub('sklearn.preprocessing')
_make_stub('sklearn.utils')
_make_stub('sklearn.utils._param_validation')
_make_stub('tensorflow')
_make_stub('transformers')
_make_stub('joblib')
_make_stub('scipy')
_make_stub('scipy.sparse')

# Stub the entire ml package tree so gov blueprints can import without error
_make_stub('ml')
_make_stub('ml.chroniccare')
_make_stub('ml.chroniccare.inference')
_make_stub('ml.chroniccare.model')
_make_stub('ml.nova_classifier')
_make_stub('ml.nova_classifier.inference')
_make_stub('ml.additive_scorer')
_make_stub('ml.additive_scorer.inference')
_make_stub('ml.procedure_encoder')
_make_stub('ml.procedure_encoder.inference')

# Add dummy classes/functions the blueprints expect from ML modules
ml_chronic = sys.modules['ml.chroniccare.inference']
ml_chronic.ChronicCareMLService = type('ChronicCareMLService', (), {'is_loaded': False})
ml_chronic.get_chroniccare_service = lambda: ml_chronic.ChronicCareMLService()

ml_nova = sys.modules['ml.nova_classifier.inference']
ml_nova.NovaClassificationService = type('NovaClassificationService', (), {
    'load': classmethod(lambda cls: None)
})

ml_additive = sys.modules['ml.additive_scorer.inference']
ml_additive.AdditiveRiskService = type('AdditiveRiskService', (), {
    'load': classmethod(lambda cls: None)
})

ml_proc = sys.modules['ml.procedure_encoder.inference']
ml_proc.ProcedureMatchingService = type('ProcedureMatchingService', (), {
    'load': classmethod(lambda cls: None)
})


# === Load Flask app via runpy (executes as script, no package context) ===
import runpy
app_globals = runpy.run_path(
    os.path.join(FRONTEND_DIR, 'app.py'),
    run_name='app'
)
app = app_globals['app']

"""
Vercel serverless entry point.
Uses real pandas for data + numpy-only ML inference (no PyTorch needed).
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


# === Stub heavy ML frameworks (too large for serverless) ===

def _make_stub(name):
    mod = types.ModuleType(name)
    mod.__path__ = []
    sys.modules[name] = mod
    return mod

for name in ['torch', 'torch.nn', 'torch.nn.functional', 'torch.optim',
             'torch.utils', 'torch.utils.data',
             'tensorflow', 'transformers',
             'scipy', 'scipy.sparse']:
    _make_stub(name)

# Stub torch.nn.Module so model class definitions don't crash on import
nn = sys.modules['torch.nn']
nn.Module = type('Module', (), {
    '__init__': lambda self, *a, **kw: None,
    'eval': lambda self: self,
    'parameters': lambda self: iter([]),
    'forward': lambda self, *a, **kw: None,
})
nn.Linear = lambda *a, **kw: None
nn.Dropout = lambda *a, **kw: None
nn.ReLU = lambda *a, **kw: None
nn.Sigmoid = lambda *a, **kw: None
nn.Embedding = lambda *a, **kw: None
nn.Conv1d = lambda *a, **kw: None
nn.BatchNorm1d = lambda *a, **kw: None
nn.Sequential = lambda *a, **kw: None
nn.ModuleList = lambda *a, **kw: []
nn.CrossEntropyLoss = lambda *a, **kw: None
nn.MSELoss = lambda *a, **kw: None


# === Set up ML module stubs ===
for name in ['ml', 'ml.chroniccare', 'ml.chroniccare.inference', 'ml.chroniccare.model',
             'ml.procedure_encoder', 'ml.procedure_encoder.inference']:
    _make_stub(name)

# These modules can actually import now (torch.nn.Module is stubbed):
# ml.nova_classifier, ml.additive_scorer - their model.py files will load
# but model instances won't work. We use numpy inference instead.


# === Wire numpy ML inference ===

try:
    import importlib.util
    _np_inf_path = os.path.join(PROJECT_ROOT, 'ml', 'inference_numpy.py')
    _spec = importlib.util.spec_from_file_location('inference_numpy', _np_inf_path)
    _np_mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_np_mod)
    NovaClassifierNumpy = _np_mod.NovaClassifierNumpy
    ProcedureMatcherNumpy = _np_mod.ProcedureMatcherNumpy
    _numpy_ml_available = True
except Exception as e:
    print(f"Warning: numpy ML failed to load: {e}")
    _numpy_ml_available = False


# --- NovaClassificationService (numpy) ---
class _NovaService:
    _instance = None

    @classmethod
    def load(cls):
        if cls._instance is None and _numpy_ml_available:
            try:
                cls._instance = NovaClassifierNumpy()
                print("NOVA numpy classifier loaded")
            except Exception as e:
                print(f"Warning: NOVA numpy model failed: {e}")
        return cls._instance

# Stub the nova classifier module and inject our service
_make_stub('ml.nova_classifier')
_make_stub('ml.nova_classifier.inference')
sys.modules['ml.nova_classifier.inference'].NovaClassificationService = _NovaService


# --- AdditiveRiskService (uses lookup table - model.py imports work with stubbed torch) ---
_make_stub('ml.additive_scorer')
_make_stub('ml.additive_scorer.inference')

class _AdditiveService:
    _instance = None

    @classmethod
    def load(cls):
        if cls._instance is None:
            try:
                import pandas as pd

                lookup_csv = Path(PROJECT_ROOT) / 'data' / 'raw' / 'foodscore' / 'additive_risks.csv'
                lookup_parquet = Path(PROJECT_ROOT) / 'data' / 'processed' / 'foodscore' / 'additive_lookup.parquet'

                if lookup_csv.exists():
                    lookup_df = pd.read_csv(lookup_csv)
                elif lookup_parquet.exists():
                    lookup_df = pd.read_parquet(lookup_parquet)
                else:
                    return None

                # Build a simple service that uses lookup table scores
                service = type('AdditiveRiskService', (), {
                    'model': None,
                    'lookup_df': lookup_df,
                    'device': 'cpu',
                    '_name_index': {},
                })()

                # Build name index
                for idx, row in lookup_df.iterrows():
                    name = row["name"].lower().strip()
                    service._name_index[name] = idx

                # Bind methods from the real service class
                from dataclasses import dataclass

                @dataclass
                class AdditiveRiskResult:
                    name: str
                    risk_score: float
                    risk_category: str
                    risk_description: str = ''
                    fda_status: str = 'unknown'
                    eu_status: str = 'unknown'
                    additive_type: str = 'unknown'
                    is_artificial: bool = False
                    notes: str = None

                def _get_risk_category(score):
                    if score < 30: return 'low'
                    if score < 70: return 'moderate'
                    return 'high'

                def score_additive(self, name):
                    name_lower = name.lower().strip()
                    idx = self._name_index.get(name_lower)
                    if idx is None:
                        # Fuzzy match
                        for key, i in self._name_index.items():
                            if name_lower in key or key in name_lower:
                                idx = i
                                break
                    if idx is None:
                        return AdditiveRiskResult(name=name, risk_score=50.0,
                            risk_category='moderate', fda_status='unknown', eu_status='unknown')

                    row = self.lookup_df.iloc[idx]
                    score = float(row.get('risk_score', 50))
                    return AdditiveRiskResult(
                        name=str(row.get('name', name)),
                        risk_score=score,
                        risk_category=_get_risk_category(score),
                        fda_status=str(row.get('fda_status', 'unknown')),
                        eu_status=str(row.get('eu_status', 'unknown')),
                        additive_type=str(row.get('type', 'unknown')),
                        is_artificial=bool(row.get('is_artificial', False)),
                    )

                def score_batch(self, names):
                    return [self.score_additive(n) for n in names]

                def score_product_ingredients(self, text):
                    ingredients = [i.strip() for i in text.split(",") if i.strip()]
                    found = []
                    for ing in ingredients:
                        name_lower = ing.lower().strip()
                        if name_lower in self._name_index or any(name_lower in k or k in name_lower for k in self._name_index):
                            found.append(self.score_additive(ing))
                    scores = [a.risk_score for a in found] if found else [0]
                    return {
                        'ingredient_count': len(ingredients),
                        'additive_count': len(found),
                        'additives': found,
                        'max_risk_score': max(scores) if scores else 0,
                        'avg_risk_score': sum(scores)/len(scores) if scores else 0,
                        'high_risk_additives': [a for a in found if a.risk_category == 'high'],
                        'moderate_risk_additives': [a for a in found if a.risk_category == 'moderate'],
                        'overall_risk': _get_risk_category(max(scores)) if found else 'low',
                    }

                import types as t
                service.score_additive = t.MethodType(score_additive, service)
                service.score_batch = t.MethodType(score_batch, service)
                service.score_product_ingredients = t.MethodType(score_product_ingredients, service)

                cls._instance = service
                print(f"Additive service loaded ({len(lookup_df)} additives)")
            except Exception as e:
                print(f"Warning: Additive service failed: {e}")
        return cls._instance

sys.modules['ml.additive_scorer.inference'].AdditiveRiskService = _AdditiveService


# --- ProcedureMatchingService (numpy cosine similarity) ---
class _ProcedureService:
    _instance = None

    @classmethod
    def load(cls):
        if cls._instance is None and _numpy_ml_available:
            try:
                cls._instance = ProcedureMatcherNumpy()
                print("Procedure matcher loaded (numpy)")
            except Exception as e:
                print(f"Warning: Procedure matcher failed: {e}")
        return cls._instance

sys.modules['ml.procedure_encoder.inference'].ProcedureMatchingService = _ProcedureService


# --- ChronicCare (gov-only, stub is fine for public portal) ---
class _ChronicStub:
    is_loaded = False
    @classmethod
    def load(cls): return None

sys.modules['ml.chroniccare.inference'].ChronicCareMLService = _ChronicStub
sys.modules['ml.chroniccare.inference'].ChronicRiskService = _ChronicStub
sys.modules['ml.chroniccare.inference'].InterventionPrioritizationService = _ChronicStub
sys.modules['ml.chroniccare.inference'].get_chroniccare_service = lambda: _ChronicStub()


# === Load Flask app ===
from app import app


@app.errorhandler(500)
def vercel_error_handler(e):
    from flask import render_template, jsonify, request
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Internal server error', 'message': str(e)}), 500
    try:
        return render_template('landing.html',
                               modules=app.config.get('MODULES', {})), 500
    except Exception:
        return "<h1>HealthGuard America</h1><p>Something went wrong. <a href='/'>Home</a></p>", 500

"""
Vercel serverless entry point.
Loads real data with pandas — only stubs heavy ML packages (torch, tensorflow, sklearn).
All tracked data files (~62MB) work natively on Vercel.
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


# === Stub only heavy ML libraries (not needed for data serving) ===

def _make_stub(name):
    mod = types.ModuleType(name)
    mod.__path__ = []
    sys.modules[name] = mod
    return mod


# ML framework stubs — these are too large for serverless
for name in ['torch', 'torch.nn', 'torch.nn.functional', 'torch.optim',
             'torch.utils', 'torch.utils.data',
             'tensorflow', 'transformers',
             'scipy', 'scipy.sparse']:
    _make_stub(name)

# ML inference module stubs — models aren't deployed to Vercel
for name in ['ml', 'ml.chroniccare', 'ml.chroniccare.inference', 'ml.chroniccare.model',
             'ml.nova_classifier', 'ml.nova_classifier.inference',
             'ml.additive_scorer', 'ml.additive_scorer.inference',
             'ml.procedure_encoder', 'ml.procedure_encoder.inference']:
    _make_stub(name)


# Dummy ML service classes so route code doesn't crash
class _StubMLService:
    is_loaded = False
    @classmethod
    def load(cls): return None


sys.modules['ml.chroniccare.inference'].ChronicCareMLService = _StubMLService
sys.modules['ml.chroniccare.inference'].ChronicRiskService = _StubMLService
sys.modules['ml.chroniccare.inference'].InterventionPrioritizationService = _StubMLService
sys.modules['ml.chroniccare.inference'].get_chroniccare_service = lambda: _StubMLService()
sys.modules['ml.nova_classifier.inference'].NovaClassificationService = _StubMLService
sys.modules['ml.additive_scorer.inference'].AdditiveRiskService = _StubMLService
sys.modules['ml.procedure_encoder.inference'].ProcedureMatchingService = _StubMLService


# === Load Flask app — pandas/numpy/pyarrow work natively ===
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

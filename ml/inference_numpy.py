"""
Numpy-only ML inference for Vercel deployment.
Replaces PyTorch models with pure numpy forward passes.
All weights loaded from .npz files (pre-extracted from .pt checkpoints).
"""
import numpy as np
import json
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict

WEIGHTS_DIR = Path(__file__).parent / 'weights' / 'numpy'


# ============================================
# Numpy building blocks
# ============================================

def relu(x):
    return np.maximum(x, 0)

def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -500, 500)))

def softmax(x, axis=-1):
    e = np.exp(x - np.max(x, axis=axis, keepdims=True))
    return e / e.sum(axis=axis, keepdims=True)

def linear(x, weight, bias):
    return x @ weight.T + bias

def batchnorm(x, running_mean, running_var, weight, bias, eps=1e-5):
    return (x - running_mean) / np.sqrt(running_var + eps) * weight + bias

def conv1d(x, weight, bias, padding='same'):
    """1D convolution: x is [batch, channels_in, length], weight is [channels_out, channels_in, kernel]."""
    batch, c_in, length = x.shape
    c_out, _, kernel = weight.shape
    if padding == 'same':
        pad = kernel // 2
        x = np.pad(x, ((0, 0), (0, 0), (pad, pad)))
    out = np.zeros((batch, c_out, length))
    for i in range(c_out):
        for j in range(c_in):
            out[:, i, :] += np.convolve(x[0, j, :], weight[i, j, ::-1], mode='valid').reshape(1, -1).repeat(batch, axis=0) if batch == 1 else np.array([np.convolve(x[b, j, :], weight[i, j, ::-1], mode='valid') for b in range(batch)])
    return out + bias.reshape(1, -1, 1)


def conv1d_batch(x, weight, bias):
    """Optimized 1D convolution for batch processing."""
    batch, c_in, length = x.shape
    c_out, _, kernel = weight.shape
    pad = kernel // 2
    x_pad = np.pad(x, ((0, 0), (0, 0), (pad, pad)))
    out = np.zeros((batch, c_out, length))
    for b in range(batch):
        for co in range(c_out):
            for ci in range(c_in):
                out[b, co] += np.correlate(x_pad[b, ci], weight[co, ci], mode='valid')
    return out + bias.reshape(1, -1, 1)


# ============================================
# NOVA Classifier (Embedding + Conv1d + MLP)
# ============================================

class NovaClassifierNumpy:
    """NOVA food classification using numpy only."""

    def __init__(self, weights_path=None, tokenizer_path=None, temperature=1.0):
        weights_path = weights_path or WEIGHTS_DIR / 'nova_classifier.npz'
        tokenizer_path = tokenizer_path or Path(__file__).parent / 'weights' / 'nova_tokenizer.json'

        w = np.load(weights_path)
        self.embedding = w['embedding.weight']  # [vocab, 128]
        self.conv_w = w['conv1d.weight']  # [256, 128, 3]
        self.conv_b = w['conv1d.bias']  # [256]

        # Classifier layers: Linear(256,256) -> BN -> ReLU -> Linear(256,128) -> BN -> ReLU -> Linear(128,4)
        self.fc1_w = w['classifier.0.weight']
        self.fc1_b = w['classifier.0.bias']
        self.bn1_w = w['classifier.2.weight']
        self.bn1_b = w['classifier.2.bias']
        self.bn1_mean = w['classifier.2.running_mean']
        self.bn1_var = w['classifier.2.running_var']

        self.fc2_w = w['classifier.4.weight']
        self.fc2_b = w['classifier.4.bias']
        self.bn2_w = w['classifier.6.weight']
        self.bn2_b = w['classifier.6.bias']
        self.bn2_mean = w['classifier.6.running_mean']
        self.bn2_var = w['classifier.6.running_var']

        self.fc3_w = w['classifier.8.weight']
        self.fc3_b = w['classifier.8.bias']

        self.temperature = temperature

        # Load temperature from JSON if available
        temp_path = WEIGHTS_DIR / 'nova_temperature.json'
        if temp_path.exists():
            with open(temp_path) as f:
                self.temperature = json.load(f)['temperature']

        # Load tokenizer directly (avoid importing from stubbed ml.nova_classifier)
        import importlib.util
        tok_module_path = Path(__file__).parent / 'nova_classifier' / 'tokenizer.py'
        spec = importlib.util.spec_from_file_location('_tokenizer', str(tok_module_path))
        tok_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tok_mod)
        self.tokenizer = tok_mod.IngredientTokenizer.load(str(tokenizer_path))

    def forward(self, input_ids):
        """Forward pass: input_ids [batch, seq_len] -> logits [batch, 4]."""
        # Embedding lookup
        x = self.embedding[input_ids]  # [batch, seq_len, 128]

        # Conv1d expects [batch, channels, length]
        x = x.transpose(0, 2, 1)  # [batch, 128, seq_len]
        x = conv1d_batch(x, self.conv_w, self.conv_b)  # [batch, 256, seq_len]
        x = relu(x)

        # Global average pooling
        x = x.mean(axis=2)  # [batch, 256]

        # Classifier
        x = linear(x, self.fc1_w, self.fc1_b)
        x = batchnorm(x, self.bn1_mean, self.bn1_var, self.bn1_w, self.bn1_b)
        x = relu(x)

        x = linear(x, self.fc2_w, self.fc2_b)
        x = batchnorm(x, self.bn2_mean, self.bn2_var, self.bn2_w, self.bn2_b)
        x = relu(x)

        logits = linear(x, self.fc3_w, self.fc3_b)
        return logits

    def classify(self, ingredients_text):
        """Classify ingredients -> NovaClassification-compatible dict."""
        input_ids = self.tokenizer.encode(ingredients_text).reshape(1, -1)
        logits = self.forward(input_ids)
        logits = logits / self.temperature
        probs = softmax(logits, axis=1)[0]
        nova_group = int(np.argmax(probs)) + 1
        confidence = float(probs[nova_group - 1])

        DESCRIPTIONS = {
            1: "Unprocessed or minimally processed foods",
            2: "Processed culinary ingredients",
            3: "Processed foods",
            4: "Ultra-processed food and drink products",
        }

        return type('NovaClassification', (), {
            'ingredients_text': ingredients_text,
            'nova_group': nova_group,
            'confidence': confidence,
            'description': DESCRIPTIONS[nova_group],
            'probabilities': probs.tolist(),
            'is_confident': confidence >= 0.6,
        })()


# ============================================
# Additive Scorer (Simple MLP)
# ============================================

class AdditiveRiskScorerNumpy:
    """Additive risk scoring using numpy only."""

    def __init__(self, weights_path=None):
        weights_path = weights_path or WEIGHTS_DIR / 'additive_scorer.npz'
        w = np.load(weights_path)
        self.fc1_w = w['mlp.0.weight']  # [64, 13]
        self.fc1_b = w['mlp.0.bias']
        self.fc2_w = w['mlp.3.weight']  # [32, 64]
        self.fc2_b = w['mlp.3.bias']
        self.fc3_w = w['mlp.6.weight']  # [1, 32]
        self.fc3_b = w['mlp.6.bias']

    def predict(self, features):
        """features: [batch, 13] -> risk_scores: [batch]"""
        x = relu(linear(features, self.fc1_w, self.fc1_b))
        x = relu(linear(x, self.fc2_w, self.fc2_b))
        x = sigmoid(linear(x, self.fc3_w, self.fc3_b)) * 100.0
        return x.squeeze(-1)


# ============================================
# Chronic Risk Predictor (MLP + BatchNorm + Multi-head)
# ============================================

class ChronicRiskPredictorNumpy:
    """Chronic disease risk prediction using numpy only."""

    DISEASES = ['diabetes', 'obesity', 'heart_disease', 'high_bp', 'copd', 'depression']

    def __init__(self, weights_path=None, scaler_path=None):
        weights_path = weights_path or WEIGHTS_DIR / 'chronic_risk_predictor.npz'
        scaler_path = scaler_path or WEIGHTS_DIR / 'chronic_feature_scaler.json'

        w = np.load(weights_path)

        # Shared encoder: 3 layers of Linear -> BatchNorm -> ReLU
        self.enc = []
        for i, (lin_idx, bn_idx) in enumerate([(0, 1), (4, 5), (8, 9)]):
            self.enc.append({
                'w': w[f'shared_encoder.{lin_idx}.weight'],
                'b': w[f'shared_encoder.{lin_idx}.bias'],
                'bn_w': w[f'shared_encoder.{bn_idx}.weight'],
                'bn_b': w[f'shared_encoder.{bn_idx}.bias'],
                'bn_mean': w[f'shared_encoder.{bn_idx}.running_mean'],
                'bn_var': w[f'shared_encoder.{bn_idx}.running_var'],
            })

        # Task heads: 6 heads, each Linear(64,32) -> ReLU -> Linear(32,1)
        self.heads = []
        for i in range(6):
            self.heads.append({
                'w1': w[f'task_heads.{i}.0.weight'],
                'b1': w[f'task_heads.{i}.0.bias'],
                'w2': w[f'task_heads.{i}.2.weight'],
                'b2': w[f'task_heads.{i}.2.bias'],
            })

        # Scaler
        self.scaler_means = None
        self.scaler_stds = None
        if Path(scaler_path).exists():
            with open(scaler_path) as f:
                scaler = json.load(f)
                self.scaler_means = np.array(scaler['means'])
                self.scaler_stds = np.array(scaler['stds'])

    def scale(self, features):
        if self.scaler_means is not None:
            stds = np.where(self.scaler_stds == 0, 1, self.scaler_stds)
            return (features - self.scaler_means) / stds
        return features

    def predict(self, features):
        """features: [batch, 19] -> predictions: [batch, 6]"""
        x = self.scale(features.astype(np.float32))

        # Shared encoder
        for layer in self.enc:
            x = linear(x, layer['w'], layer['b'])
            x = batchnorm(x, layer['bn_mean'], layer['bn_var'], layer['bn_w'], layer['bn_b'])
            x = relu(x)

        # Task heads
        outputs = []
        for head in self.heads:
            h = relu(linear(x, head['w1'], head['b1']))
            h = linear(x, head['w2'], head['b2']) if head['w2'].shape[1] == x.shape[-1] else linear(h, head['w2'], head['b2'])
            outputs.append(h)

        return np.concatenate(outputs, axis=-1)


# ============================================
# Intervention Prioritizer (MLP + BatchNorm)
# ============================================

class InterventionPrioritizerNumpy:
    """Intervention priority classification using numpy only."""

    CLASSES = ['critical', 'high', 'medium', 'low']

    def __init__(self, weights_path=None, scaler_path=None):
        weights_path = weights_path or WEIGHTS_DIR / 'intervention_prioritizer.npz'
        scaler_path = scaler_path or WEIGHTS_DIR / 'intervention_feature_scaler.json'

        w = np.load(weights_path)

        self.enc = []
        for lin_idx, bn_idx in [(0, 1), (4, 5), (8, 9)]:
            key_w = f'encoder.{lin_idx}.weight'
            if key_w not in w:
                break
            self.enc.append({
                'w': w[f'encoder.{lin_idx}.weight'],
                'b': w[f'encoder.{lin_idx}.bias'],
                'bn_w': w[f'encoder.{bn_idx}.weight'],
                'bn_b': w[f'encoder.{bn_idx}.bias'],
                'bn_mean': w[f'encoder.{bn_idx}.running_mean'],
                'bn_var': w[f'encoder.{bn_idx}.running_var'],
            })

        self.head_w = w['classifier.0.weight']
        self.head_b = w['classifier.0.bias']

        self.scaler_means = None
        self.scaler_stds = None
        if Path(scaler_path).exists():
            with open(scaler_path) as f:
                scaler = json.load(f)
                self.scaler_means = np.array(scaler['means'])
                self.scaler_stds = np.array(scaler['stds'])

    def scale(self, features):
        if self.scaler_means is not None:
            stds = np.where(self.scaler_stds == 0, 1, self.scaler_stds)
            return (features - self.scaler_means) / stds
        return features

    def predict(self, features):
        """features: [batch, 16] -> class_probs: [batch, 4]"""
        x = self.scale(features.astype(np.float32))
        for layer in self.enc:
            x = linear(x, layer['w'], layer['b'])
            x = batchnorm(x, layer['bn_mean'], layer['bn_var'], layer['bn_w'], layer['bn_b'])
            x = relu(x)
        logits = linear(x, self.head_w, self.head_b)
        return softmax(logits, axis=-1)


# ============================================
# Procedure Matching (cosine similarity on pre-computed embeddings)
# ============================================

class ProcedureMatcherNumpy:
    """Procedure matching using pre-computed embeddings + cosine similarity.
    No BERT model needed — uses TF-IDF-like text matching for query encoding."""

    def __init__(self, embeddings_path=None):
        embeddings_path = embeddings_path or WEIGHTS_DIR / 'procedure_embeddings.npz'
        data = np.load(embeddings_path, allow_pickle=True)
        self.embeddings = data['embeddings']  # [6405, 384]
        self.codes = data['codes'].tolist()
        self.descriptions = data['descriptions'].tolist()

        # Build text index for fast lookup
        self._desc_lower = [d.lower() for d in self.descriptions]
        self._code_to_idx = {c: i for i, c in enumerate(self.codes)}

    def find_similar(self, query, top_k=5):
        """Find most similar procedures by text matching.
        Returns list of (code, description, confidence) tuples."""
        query_lower = query.lower().strip()
        scores = []

        for i, desc in enumerate(self._desc_lower):
            # Simple text similarity score
            score = 0
            query_words = set(query_lower.split())
            desc_words = set(desc.split())

            # Exact substring match
            if query_lower in desc:
                score = 0.9
            elif desc in query_lower:
                score = 0.85
            else:
                # Word overlap (Jaccard-like)
                overlap = query_words & desc_words
                if overlap:
                    score = len(overlap) / max(len(query_words | desc_words), 1) * 0.8

            if score > 0.1:
                scores.append((i, score))

        # Sort by score
        scores.sort(key=lambda x: x[1], reverse=True)

        results = []
        for idx, score in scores[:top_k]:
            results.append((self.codes[idx], self.descriptions[idx], score))

        return results

    def match(self, description):
        """Match a single description. Returns ProcedureMatch-like object."""
        results = self.find_similar(description, top_k=1)
        if results:
            code, desc, conf = results[0]
            status = 'matched' if conf >= 0.8 else 'review' if conf >= 0.65 else 'unmatched'
            return type('ProcedureMatch', (), {
                'input_description': description,
                'matched_code': code,
                'matched_description': desc,
                'confidence': conf,
                'status': status,
            })()
        return type('ProcedureMatch', (), {
            'input_description': description,
            'matched_code': None,
            'matched_description': None,
            'confidence': 0.0,
            'status': 'unmatched',
        })()

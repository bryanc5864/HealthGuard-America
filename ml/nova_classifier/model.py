"""
NOVA Classifier Model - Custom CNN for ingredient text classification.

Architecture (from spec):
    Embedding(vocab_size, 128)
    → Conv1D(256 filters, kernel=3)
    → ReLU
    → GlobalAveragePooling
    → Dense(256) → ReLU → BatchNorm → Dropout(0.3)
    → Dense(128) → ReLU → BatchNorm → Dropout(0.3)
    → Dense(4) → Softmax

This captures local patterns in ingredient lists like:
- "high fructose corn syrup" (NOVA 4 indicator)
- "partially hydrogenated" (NOVA 4 indicator)
- Combinations of emulsifiers and stabilizers
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional, Dict
import numpy as np


class NovaClassifier(nn.Module):
    """
    CNN classifier for NOVA food processing level.

    Takes tokenized ingredient text and outputs 4-class probabilities.
    """

    def __init__(
        self,
        vocab_size: int = 10000,
        embedding_dim: int = 128,
        conv_filters: int = 256,
        conv_kernel_size: int = 3,
        hidden_dims: tuple = (256, 128),
        num_classes: int = 4,
        dropout: float = 0.3,
        padding_idx: int = 0,
    ):
        """
        Initialize the classifier.

        Args:
            vocab_size: Size of vocabulary
            embedding_dim: Dimension of token embeddings
            conv_filters: Number of convolutional filters
            conv_kernel_size: Size of convolutional kernel
            hidden_dims: Dimensions of hidden layers
            num_classes: Number of output classes (4 for NOVA)
            dropout: Dropout probability
            padding_idx: Index for padding token (ignored in embedding)
        """
        super().__init__()

        self.vocab_size = vocab_size
        self.embedding_dim = embedding_dim
        self.num_classes = num_classes

        # Embedding layer
        self.embedding = nn.Embedding(
            vocab_size,
            embedding_dim,
            padding_idx=padding_idx,
        )

        # 1D Convolution
        self.conv1d = nn.Conv1d(
            in_channels=embedding_dim,
            out_channels=conv_filters,
            kernel_size=conv_kernel_size,
            padding=conv_kernel_size // 2,  # Same padding
        )

        # Classification head
        layers = []
        in_features = conv_filters

        for hidden_dim in hidden_dims:
            layers.extend([
                nn.Linear(in_features, hidden_dim),
                nn.ReLU(),
                nn.BatchNorm1d(hidden_dim),
                nn.Dropout(dropout),
            ])
            in_features = hidden_dim

        # Output layer
        layers.append(nn.Linear(in_features, num_classes))

        self.classifier = nn.Sequential(*layers)

    def forward(self, input_ids: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.

        Args:
            input_ids: Token IDs [batch_size, seq_len]

        Returns:
            logits: Class logits [batch_size, num_classes]
        """
        # Embedding [batch, seq, embed_dim]
        x = self.embedding(input_ids)

        # Conv1D expects [batch, channels, seq]
        x = x.permute(0, 2, 1)

        # Convolutional layer [batch, conv_filters, seq]
        x = self.conv1d(x)
        x = F.relu(x)

        # Global average pooling [batch, conv_filters]
        x = x.mean(dim=2)

        # Classification head [batch, num_classes]
        logits = self.classifier(x)

        return logits

    def predict(self, input_ids: torch.Tensor) -> torch.Tensor:
        """
        Get class predictions.

        Args:
            input_ids: Token IDs [batch_size, seq_len]

        Returns:
            predictions: Predicted classes [batch_size]
        """
        logits = self.forward(input_ids)
        return torch.argmax(logits, dim=1)

    def predict_proba(self, input_ids: torch.Tensor) -> torch.Tensor:
        """
        Get class probabilities.

        Args:
            input_ids: Token IDs [batch_size, seq_len]

        Returns:
            probabilities: Class probabilities [batch_size, num_classes]
        """
        logits = self.forward(input_ids)
        return F.softmax(logits, dim=1)

    def save(self, path: str, tokenizer_path: Optional[str] = None) -> None:
        """Save model weights and config."""
        torch.save({
            "model_state_dict": self.state_dict(),
            "config": {
                "vocab_size": self.vocab_size,
                "embedding_dim": self.embedding_dim,
                "num_classes": self.num_classes,
            },
        }, path)
        print(f"Model saved to {path}")

    @classmethod
    def load(cls, path: str, device: str = "cpu") -> "NovaClassifier":
        """Load model from checkpoint."""
        checkpoint = torch.load(path, map_location=device)

        config = checkpoint["config"]
        model = cls(
            vocab_size=config["vocab_size"],
            embedding_dim=config["embedding_dim"],
            num_classes=config["num_classes"],
        )
        model.load_state_dict(checkpoint["model_state_dict"])
        model.to(device)
        model.eval()

        print(f"Model loaded from {path}")
        return model


class TemperatureScaledNovaClassifier(nn.Module):
    """
    NOVA Classifier with temperature scaling for calibrated confidence.

    Temperature scaling adjusts the softmax temperature so that
    confidence scores better reflect actual accuracy.
    """

    def __init__(self, model: NovaClassifier, temperature: float = 1.0):
        super().__init__()
        self.model = model
        self.temperature = nn.Parameter(torch.tensor(temperature))

    def forward(self, input_ids: torch.Tensor) -> torch.Tensor:
        """Get temperature-scaled logits."""
        logits = self.model(input_ids)
        return logits / self.temperature

    def predict_proba(self, input_ids: torch.Tensor) -> torch.Tensor:
        """Get calibrated probabilities."""
        logits = self.forward(input_ids)
        return F.softmax(logits, dim=1)

    def calibrate(
        self,
        val_loader,
        device: str = "cpu",
        max_iter: int = 50,
    ) -> float:
        """
        Learn optimal temperature on validation set.

        Args:
            val_loader: Validation DataLoader
            device: Device
            max_iter: Maximum optimization iterations

        Returns:
            Learned temperature value
        """
        self.model.eval()

        # Collect logits and labels
        logits_list = []
        labels_list = []

        with torch.no_grad():
            for batch in val_loader:
                input_ids = batch["input_ids"].to(device)
                labels = batch["labels"].to(device)

                logits = self.model(input_ids)
                logits_list.append(logits)
                labels_list.append(labels)

        logits = torch.cat(logits_list)
        labels = torch.cat(labels_list)

        # Optimize temperature
        optimizer = torch.optim.LBFGS([self.temperature], lr=0.01, max_iter=max_iter)

        def closure():
            optimizer.zero_grad()
            loss = F.cross_entropy(logits / self.temperature, labels)
            loss.backward()
            return loss

        optimizer.step(closure)

        print(f"Calibrated temperature: {self.temperature.item():.3f}")
        return self.temperature.item()

"""Thirty-layer paper-signal model with incremental learning after 10 compatible closes."""
import math
import os

from feature_engine import FEATURE_VERSION

MODEL_PATH = "solana_model.pt"
GATE_CLOSED = 10
MODEL_ARCH_VERSION = "deep30x128-v1"

try:
    import torch
    from torch import nn

    class DeepSignalModel(nn.Module):
        def __init__(self, input_dim=1205):
            super().__init__()
            layers = []
            dim = input_dim
            for _ in range(30):
                layers.extend([nn.Linear(dim, 128), nn.ReLU(), nn.Dropout(0.08)])
                dim = 128
            layers.append(nn.Linear(dim, 1))
            self.net = nn.Sequential(*layers)

        def forward(self, x):
            return self.net(x)
except ImportError:
    torch = None
    DeepSignalModel = None
    nn = None


def _outcome(item):
    try:
        net = float(item.get("net_return_pct"))
        if math.isfinite(net):
            return 1 if net > 0 else 0
    except (TypeError, ValueError):
        pass
    return 1 if item.get("status") == "TP" else 0


def _valid_features(item):
    features = item.get("features")
    if not isinstance(features, dict) or len(features) != 1205:
        return False
    version = item.get("feature_version")
    if version not in (None, FEATURE_VERSION):
        return False
    try:
        return all(math.isfinite(float(value)) for value in features.values())
    except (TypeError, ValueError):
        return False


def gate_status(history):
    closed = [x for x in history if x.get("status") in ("TP", "SL")]
    compatible = [x for x in closed if _valid_features(x)]
    wins = sum(1 for item in closed if _outcome(item) == 1)
    return {
        "closed_signals": len(closed),
        "compatible_signals": len(compatible),
        "required_closed": GATE_CLOSED,
        "wins": wins,
        "losses": len(closed) - wins,
        "enabled": len(compatible) >= GATE_CLOSED,
    }


def _load_checkpoint():
    if torch is None or not os.path.isfile(MODEL_PATH):
        return None
    try:
        data = torch.load(MODEL_PATH, map_location="cpu", weights_only=False)
        if (data.get("feature_version") != FEATURE_VERSION
                or data.get("architecture") != MODEL_ARCH_VERSION
                or int(data.get("input_dim", 0)) != 1205
                or not isinstance(data.get("feature_mean"), list)
                or not isinstance(data.get("feature_std"), list)
                or len(data["feature_mean"]) != 1205
                or len(data["feature_std"]) != 1205):
            return None
        return data
    except Exception:
        return None


def train(history, epochs=2):
    gate = gate_status(history)
    if torch is None:
        return {"trained": False, "reason": "torch unavailable", "gate": gate}
    if not gate["enabled"]:
        return {"trained": False, "reason": "10 closed signals with compatible feature snapshots required", "gate": gate}

    eligible = [item for item in history
                if item.get("status") in ("TP", "SL") and _valid_features(item)]
    keys = sorted(eligible[0]["features"])
    if any(sorted(item["features"]) != keys for item in eligible):
        return {"trained": False, "reason": "feature schema mismatch", "gate": gate}

    rows = [[float(item["features"][key]) for key in keys] for item in eligible]
    labels = [_outcome(item) for item in eligible]
    split = max(1, int(len(rows) * 0.8))
    if split >= len(rows):
        split = len(rows) - 1

    raw_train = torch.tensor(rows[:split], dtype=torch.float32)
    raw_val = torch.tensor(rows[split:], dtype=torch.float32)
    y = torch.tensor(labels[:split], dtype=torch.float32).view(-1, 1)
    yv = torch.tensor(labels[split:], dtype=torch.float32).view(-1, 1)

    # Keep the original scaler when resuming so existing weights retain the same input meaning.
    previous = _load_checkpoint()
    if previous:
        mean = torch.tensor(previous["feature_mean"], dtype=torch.float32)
        std = torch.tensor(previous["feature_std"], dtype=torch.float32).clamp_min(1e-6)
    else:
        mean = raw_train.mean(dim=0)
        std = raw_train.std(dim=0, unbiased=False).clamp_min(1e-6)

    x = ((raw_train - mean) / std).clamp(-10.0, 10.0)
    xv = ((raw_val - mean) / std).clamp(-10.0, 10.0)

    model = DeepSignalModel(len(keys))
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
    if previous:
        try:
            model.load_state_dict(previous["state_dict"])
            if previous.get("optimizer_state_dict"):
                optimizer.load_state_dict(previous["optimizer_state_dict"])
        except Exception:
            # A damaged/incompatible optimizer must not prevent safe retraining.
            model = DeepSignalModel(len(keys))
            optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)

    loss_fn = nn.BCEWithLogitsLoss()
    model.train()
    for _ in range(max(1, int(epochs))):
        optimizer.zero_grad()
        loss = loss_fn(model(x), y)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

    model.eval()
    with torch.no_grad():
        val_logits = model(xv) if len(xv) else None
        val_loss = float(loss_fn(val_logits, yv)) if val_logits is not None else None
        val_probs = torch.sigmoid(val_logits) if val_logits is not None else None
        val_accuracy = float(((val_probs >= 0.5) == (yv >= 0.5)).float().mean()) if val_probs is not None else None
        val_brier = float(((val_probs - yv) ** 2).mean()) if val_probs is not None else None

    torch.save({
        "state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "input_dim": len(keys),
        "feature_version": FEATURE_VERSION,
        "architecture": MODEL_ARCH_VERSION,
        "feature_mean": mean.tolist(),
        "feature_std": std.tolist(),
        "trained_samples": len(rows),
        "trained_wins": sum(labels),
        "trained_losses": len(labels) - sum(labels),
    }, MODEL_PATH)

    return {
        "trained": True,
        "samples": len(rows),
        "train_samples": len(x),
        "validation_samples": len(xv),
        "train_loss": float(loss.detach()),
        "validation_loss": val_loss,
        "validation_accuracy": val_accuracy,
        "validation_brier": val_brier,
        "resumed_previous_model": bool(previous),
        "gate": gate,
        "warning": "Early-stage model: small sample size; probability is experimental.",
    }


def predict_probability(features):
    if torch is None or not isinstance(features, dict) or len(features) != 1205:
        return None
    data = _load_checkpoint()
    if data is None:
        return None
    try:
        keys = sorted(features)
        values = [float(features[key]) for key in keys]
        if not all(math.isfinite(value) for value in values):
            return None
        model = DeepSignalModel(len(keys))
        model.load_state_dict(data["state_dict"])
        model.eval()
        mean = torch.tensor(data["feature_mean"], dtype=torch.float32)
        std = torch.tensor(data["feature_std"], dtype=torch.float32).clamp_min(1e-6)
        sample = torch.tensor([values], dtype=torch.float32)
        sample = ((sample - mean) / std).clamp(-10.0, 10.0)
        with torch.no_grad():
            value = torch.sigmoid(model(sample)).item()
        return float(value) if math.isfinite(value) else None
    except Exception:
        return None

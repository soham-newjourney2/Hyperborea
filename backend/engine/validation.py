"""P22 validation metrics (pure): worst rain window, contingency scores, threshold-free ranking AUC."""
from __future__ import annotations


def worst(p: list[float], w: int) -> tuple[int, float]:
    i = max(range(len(p) - w + 1), key=lambda k: sum(p[k:k + w]))
    return i, sum(p[i:i + w])


def scores(obs: set, pred: set, universe: set) -> dict:
    tp, fp, fn = len(obs & pred), len(pred - obs), len(obs - pred)
    tn = len(universe) - tp - fp - fn
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "pod": round(tp / (tp + fn), 3) if tp + fn else None,
            "far": round(fp / (tp + fp), 3) if tp + fp else None,
            "csi": round(tp / (tp + fp + fn), 3) if tp + fp + fn else None}


def auc(obs: set, score: dict) -> float | None:
    """Ranking skill independent of the flag threshold (0.5 = random). Ties (e.g. many zero depths) count half."""
    from sklearn.metrics import roc_auc_score
    ids = list(score)
    y = [c in obs for c in ids]
    if len(set(y)) < 2:
        return None
    return round(float(roc_auc_score(y, [score[c] for c in ids])), 3)

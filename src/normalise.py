SPREAD_FLAG_PP = 10.0
CONSENSUS_FLAG_PP = 5.0


def normalise(probs: dict) -> dict:
    if any(v < 0 for v in probs.values()):
        raise ValueError("negative probability")
    total = sum(probs.values())
    if total <= 0:
        raise ValueError("probabilities sum to zero")
    return {k: v / total * 100 for k, v in probs.items()}


def consensus(models: list) -> dict:
    keys = models[0].keys()
    mean = {k: sum(m[k] for m in models) / len(models) for k in keys}
    spread = {k: max(m[k] for m in models) - min(m[k] for m in models) for k in keys}
    return {"mean": mean, "spread": spread}


def flags(models: list) -> dict:
    if len(models) < 2:
        return {"low_confidence": True, "consensus_gap": False, "model_spread": False}
    c = consensus(models)
    gap = any(abs(m[k] - c["mean"][k]) >= CONSENSUS_FLAG_PP - 1e-9 for m in models for k in m)
    spread = any(v >= SPREAD_FLAG_PP - 1e-9 for v in c["spread"].values())
    return {"low_confidence": False, "consensus_gap": gap, "model_spread": spread}

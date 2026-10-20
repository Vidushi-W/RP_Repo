"""Stable vocabulary and checkpoint continuation for the single studio model."""
import copy
import json
from pathlib import Path
import torch


def continuing_vocabulary(signs, source: Path | None):
    labels = ["<blank>"]
    if source:
        labels = json.loads((source / "vocabulary.json").read_text())["labels"]
        if not labels or labels[0] != "<blank>":
            raise ValueError("Checkpoint has an incompatible blank token")
    labels = labels + sorted(set(signs) - set(labels))
    return {"labels": labels, "blank_index": 0, "blank_token": "<blank>",
            "label_to_id": {v: i for i, v in enumerate(labels)},
            "id_to_label": {str(i): v for i, v in enumerate(labels)}}


def restore_training(model, optimizer, source: Path):
    previous = torch.load(source / "model.pt", map_location="cpu", weights_only=True)
    state = model.state_dict()
    if set(previous) != set(state):
        raise ValueError("Checkpoint is missing model parameters")
    expected_classes = len(json.loads((source / "vocabulary.json").read_text())["labels"])
    if previous["classifier.weight"].shape[0] != expected_classes:
        raise ValueError("Checkpoint vocabulary does not match its classifier")
    for name, value in previous.items():
        if name not in state:
            raise ValueError(f"Incompatible checkpoint parameter: {name}")
        if state[name].shape == value.shape:
            state[name] = value
        elif name in {"classifier.weight", "classifier.bias"} and state[name].shape[0] >= value.shape[0] and state[name].shape[1:] == value.shape[1:]:
            state[name][:value.shape[0]] = value
        else:
            raise ValueError(f"Checkpoint architecture differs at {name}")
    model.load_state_dict(state)
    path = source / "optimizer.pt"
    if path.exists():
        opt = torch.load(path, map_location="cpu", weights_only=True)
        params = list(model.parameters())
        ids = [i for g in opt["param_groups"] for i in g["params"]]
        for pid, param in zip(ids, params):
            for key, value in opt["state"].get(pid, {}).items():
                if torch.is_tensor(value) and value.ndim and value.shape != param.shape:
                    if value.shape[1:] != param.shape[1:] or value.shape[0] > param.shape[0]:
                        raise ValueError("Incompatible optimizer checkpoint")
                    expanded = torch.zeros_like(param, device="cpu")
                    expanded[:value.shape[0]] = value
                    opt["state"][pid][key] = expanded
        rates = [g["lr"] for g in optimizer.param_groups]
        optimizer.load_state_dict(opt)
        for group, rate in zip(optimizer.param_groups, rates):
            group["lr"] = rate
    return path.exists()


def optimizer_snapshot(optimizer):
    result = copy.deepcopy(optimizer.state_dict())
    for state in result["state"].values():
        for key, value in state.items():
            if torch.is_tensor(value):
                state[key] = value.cpu()
    return result

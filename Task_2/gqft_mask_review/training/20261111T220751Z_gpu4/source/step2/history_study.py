"""Utilities for a leakage-resistant shortest-flow-history study.

All candidate histories must be evaluated on the same reference windows and
queries.  A history view therefore truncates only the tensors supplied to the
model; full-reference targets and 3-D displacement curves remain untouched.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Iterator, Mapping
import math

import torch
import torch.nn.functional as F


def truncate_model_input(batch: Mapping, history: int) -> dict:
    """Return a shallow batch copy with only model-input time tensors truncated."""
    if history < 1:
        raise ValueError("history must be positive")
    flow = batch["flow"]
    mask = batch["history_mask"]
    if flow.ndim < 2 or mask.ndim != 2 or flow.shape[:2] != mask.shape:
        raise ValueError("flow/history_mask batch and time dimensions disagree")
    if history > flow.shape[1] or not bool(mask[:, :history].all()):
        raise ValueError(f"reference batch does not contain history {history}")
    result = dict(batch)
    result["flow"] = flow[:, :history]
    result["history_mask"] = mask[:, :history]
    return result


class FixedTaskHistoryView:
    """Re-iterable view that changes only a reference loader's model horizon."""

    def __init__(self, reference_loader: Iterable[dict], history: int):
        self.reference_loader = reference_loader
        self.history = history

    def __iter__(self) -> Iterator[dict]:
        for batch in self.reference_loader:
            yield truncate_model_input(batch, self.history)

    def __len__(self) -> int:
        return len(self.reference_loader)  # type: ignore[arg-type]


def cross_sequence_nearest_neighbors(
        embeddings: torch.Tensor, curves: torch.Tensor, sequences: list[str]) -> dict:
    """Find embedding neighbours while excluding all same-sequence samples.

    Curves are fixed-reference camera displacement paths ``[N,T,3]``.  Thus the
    diagnostic always compares the complete future path, independently of the
    candidate input history.
    """
    if embeddings.ndim != 2:
        raise ValueError("embeddings must have shape [N,D]")
    if curves.ndim != 3 or curves.shape[0] != embeddings.shape[0] or curves.shape[2] != 3:
        raise ValueError("curves must have shape [N,T,3]")
    if len(sequences) != embeddings.shape[0]:
        raise ValueError("one sequence label is required per sample")
    n = len(sequences)
    if n < 2:
        return {
            "eligible": torch.zeros(n, dtype=torch.bool),
            "nearest_index": torch.full((n,), -1, dtype=torch.long),
            "nearest_similarity": torch.full((n,), float("nan")),
            "full_curve_gap_m": torch.full((n,), float("nan")),
            "endpoint_gap_m": torch.full((n,), float("nan")),
        }

    z = F.normalize(embeddings.float(), dim=1)
    similarity = z @ z.T
    # Build IDs without relying on hash randomisation.
    names: dict[str, int] = {}
    ids = []
    for name in sequences:
        ids.append(names.setdefault(name, len(names)))
    sequence_id = torch.tensor(ids, device=similarity.device)
    allowed = sequence_id[:, None] != sequence_id[None, :]
    eligible = allowed.any(dim=1)
    similarity = similarity.masked_fill(~allowed, -float("inf"))
    nearest_similarity, nearest = similarity.max(dim=1)
    nearest = torch.where(eligible, nearest, torch.full_like(nearest, -1))

    safe_nearest = nearest.clamp_min(0).to(curves.device)
    point_gap = torch.linalg.vector_norm(curves.float() - curves[safe_nearest].float(), dim=2)
    full_curve_gap = point_gap.mean(dim=1)
    endpoint_gap = point_gap[:, -1]
    nan = torch.full_like(full_curve_gap, float("nan"))
    full_curve_gap = torch.where(eligible.to(curves.device), full_curve_gap, nan)
    endpoint_gap = torch.where(eligible.to(curves.device), endpoint_gap, nan)
    nearest_similarity = torch.where(
        eligible, nearest_similarity, torch.full_like(nearest_similarity, float("nan")))
    return {
        "eligible": eligible.cpu(),
        "nearest_index": nearest.cpu(),
        "nearest_similarity": nearest_similarity.cpu(),
        "full_curve_gap_m": full_curve_gap.cpu(),
        "endpoint_gap_m": endpoint_gap.cpu(),
    }


class SignatureRetrievalAccumulator:
    """Collect learned terminal embeddings and full-reference motion curves."""

    def __init__(self, max_samples: int, *, cosine_threshold: float = 0.995,
                 ambiguity_curve_gap_m: float = 0.10):
        self.max_samples = max_samples
        self.cosine_threshold = cosine_threshold
        self.ambiguity_curve_gap_m = ambiguity_curve_gap_m
        self._by_sequence: dict[str, list[tuple[torch.Tensor, torch.Tensor]]] = defaultdict(list)
        self._curve_points: int | None = None

    def update(self, embeddings: torch.Tensor, curves: torch.Tensor,
               sequences: list[str]) -> None:
        if self.max_samples <= 0:
            return
        if curves.ndim != 3 or curves.shape[0] != embeddings.shape[0]:
            raise ValueError("signature/curve batch mismatch")
        if len(sequences) != embeddings.shape[0]:
            raise ValueError("signature/sequence batch mismatch")
        if self._curve_points is None:
            self._curve_points = curves.shape[1]
        elif curves.shape[1] != self._curve_points:
            raise ValueError("signature study requires one fixed reference horizon")
        embedding_cpu = embeddings.detach().float().cpu()
        curves_cpu = curves.detach().float().cpu()
        # Cap each sequence separately, then round-robin sequences at finalize.
        # This avoids a manifest's first long sequence consuming the entire cap.
        for index, sequence in enumerate(sequences):
            if len(self._by_sequence[sequence]) < self.max_samples:
                self._by_sequence[sequence].append((embedding_cpu[index], curves_cpu[index]))

    def _balanced_samples(self) -> tuple[torch.Tensor, torch.Tensor, list[str]] | None:
        selected = []
        sequence_names = list(self._by_sequence)
        depth = 0
        while len(selected) < self.max_samples:
            added = False
            for name in sequence_names:
                items = self._by_sequence[name]
                if depth < len(items):
                    selected.append((name, *items[depth]))
                    added = True
                    if len(selected) == self.max_samples:
                        break
            if not added:
                break
            depth += 1
        if not selected:
            return None
        return (torch.stack([x[1] for x in selected]),
                torch.stack([x[2] for x in selected]),
                [x[0] for x in selected])

    def compute(self) -> dict[str, float | int]:
        samples = self._balanced_samples()
        if samples is None:
            return {"signature_samples": 0, "signature_cross_sequence_eligible": 0}
        embeddings, curves, sequences = samples
        neighbours = cross_sequence_nearest_neighbors(embeddings, curves, sequences)
        eligible = neighbours["eligible"]
        result: dict[str, float | int] = {
            "signature_samples": len(sequences),
            "signature_sequences": len(set(sequences)),
            "signature_cross_sequence_eligible": int(eligible.sum()),
            "signature_reference_curve_points": curves.shape[1],
        }
        if not bool(eligible.any()):
            return result
        similarity = neighbours["nearest_similarity"][eligible]
        curve_gap = neighbours["full_curve_gap_m"][eligible]
        endpoint_gap = neighbours["endpoint_gap_m"][eligible]
        close = similarity >= self.cosine_threshold
        ambiguity = ((curve_gap[close] > self.ambiguity_curve_gap_m).float().mean()
                     if bool(close.any()) else curve_gap.new_tensor(0.0))
        result.update({
            "nn_cosine_mean": float(similarity.mean()),
            "nn_full_curve_gap_m_mean": float(curve_gap.mean()),
            "nn_endpoint_gap_m_mean": float(endpoint_gap.mean()),
            "signature_ambiguity": float(ambiguity),
            "signature_close_pairs": int(close.sum()),
            "signature_ambiguity_curve_gap_m": self.ambiguity_curve_gap_m,
        })
        return result


def select_shortest_history(results: list[dict], *, retrieval_tolerance: float,
                            max_ambiguity: float) -> int | None:
    """Select on validation retrieval quality, never on prefix path error."""
    if retrieval_tolerance < 0:
        raise ValueError("retrieval_tolerance must be non-negative")
    ordered = sorted(results, key=lambda item: int(item["history"]))
    for index, record in enumerate(ordered):
        error = record.get("nn_full_curve_gap_m_mean")
        ambiguity = record.get("signature_ambiguity")
        if error is None or ambiguity is None or not math.isfinite(float(error)):
            continue
        longer_errors = [float(item["nn_full_curve_gap_m_mean"])
                         for item in ordered[index:]
                         if item.get("nn_full_curve_gap_m_mean") is not None and
                         math.isfinite(float(item["nn_full_curve_gap_m_mean"]))]
        if not longer_errors:
            continue
        best_equal_or_longer = min(longer_errors)
        within_tolerance = float(error) <= (1.0 + retrieval_tolerance) * best_equal_or_longer
        if within_tolerance and float(ambiguity) <= max_ambiguity:
            return int(record["history"])
    return None
